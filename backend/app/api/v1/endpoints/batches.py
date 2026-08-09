"""Batch endpoints with FEFO support"""
from datetime import date
from typing import Literal, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, WarehouseUser, StaffUser, Scope
from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.location import Location
from app.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.export_service import export_service
from app.services.scoping import batch_location_filter

router = APIRouter()


@router.get("", response_model=PaginatedResponse[BatchResponse])
async def list_batches(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: Optional[UUID] = None,
    status_filter: Optional[BatchStatus] = None,
    expiring_within_days: Optional[int] = None,
    sort_by: Optional[Literal["batch_number", "quantity_available", "receipt_date", "expiration_date", "status"]] = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> PaginatedResponse[BatchResponse]:
    """List batches with FEFO sorting by default"""
    query = (
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
    )

    location_clause = batch_location_filter(scope)
    if location_clause is not None:
        query = query.where(location_clause)

    # Apply filters
    if item_id:
        query = query.where(Batch.item_id == item_id)

    if status_filter:
        query = query.where(Batch.status == status_filter)
    else:
        # By default, show only active batches
        query = query.where(Batch.status == BatchStatus.ACTIVE)

    if expiring_within_days:
        from datetime import timedelta
        expiration_threshold = date.today() + timedelta(days=expiring_within_days)
        query = query.where(Batch.expiration_date <= expiration_threshold)

    # Apply sorting — default to FEFO (expiration asc)
    if sort_by:
        col = getattr(Batch, sort_by)
        query = query.order_by(col.desc() if sort_order == "desc" else col.asc())
    else:
        query = query.order_by(Batch.expiration_date.asc())
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    batches = result.scalars().all()
    
    # Convert to response
    batch_responses = []
    for batch in batches:
        response = BatchResponse.model_validate(batch)
        response.days_until_expiration = (batch.expiration_date - date.today()).days
        response.is_expired = batch.expiration_date < date.today()
        response.inventory_value = batch.quantity_available * (batch.item.cost_price if batch.item else 0)
        response.item_sku = batch.item.sku if batch.item else None
        response.item_name = batch.item.name if batch.item else None
        response.location_code = batch.location.location_code if batch.location else None
        batch_responses.append(response)
    
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return PaginatedResponse(
        items=batch_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/expiring-soon", response_model=List[BatchResponse])
async def get_expiring_batches(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
    days: int = Query(30, ge=1, le=365),
) -> List[BatchResponse]:
    """Get batches expiring within specified days"""
    from datetime import timedelta

    expiration_threshold = date.today() + timedelta(days=days)

    query = (
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .where(
            Batch.status == BatchStatus.ACTIVE,
            Batch.expiration_date <= expiration_threshold,
            Batch.expiration_date >= date.today(),
        )
        .order_by(Batch.expiration_date.asc())
    )

    location_clause = batch_location_filter(scope)
    if location_clause is not None:
        query = query.where(location_clause)

    result = await db.execute(query)
    batches = result.scalars().all()
    
    batch_responses = []
    for batch in batches:
        response = BatchResponse.model_validate(batch)
        response.days_until_expiration = (batch.expiration_date - date.today()).days
        response.is_expired = False
        response.inventory_value = batch.quantity_available * (batch.item.cost_price if batch.item else 0)
        response.item_sku = batch.item.sku if batch.item else None
        response.item_name = batch.item.name if batch.item else None
        response.location_code = batch.location.location_code if batch.location else None
        batch_responses.append(response)
    
    return batch_responses


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> BatchResponse:
    """Get batch by ID"""
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .where(Batch.id == batch_id)
    )
    batch = result.scalar_one_or_none()

    if batch is None or (
        scope.location_ids is not None and batch.location_id not in scope.location_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="אצווה לא נמצאה",  # Batch not found
        )

    response = BatchResponse.model_validate(batch)
    response.days_until_expiration = (batch.expiration_date - date.today()).days
    response.is_expired = batch.expiration_date < date.today()
    response.inventory_value = batch.quantity_available * (batch.item.cost_price if batch.item else 0)
    response.item_sku = batch.item.sku if batch.item else None
    response.item_name = batch.item.name if batch.item else None
    response.location_code = batch.location.location_code if batch.location else None
    
    return response


@router.post("/{batch_id}/mark-scrap", response_model=BatchResponse)
async def mark_batch_as_scrap(
    batch_id: UUID,
    db: DbSession,
    current_user: WarehouseUser,
    scope: Scope,
    reason: Optional[str] = None,
) -> BatchResponse:
    """Mark a batch as scrap (גריטה)"""
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .where(Batch.id == batch_id)
    )
    batch = result.scalar_one_or_none()

    if batch is None or (
        scope.location_ids is not None and batch.location_id not in scope.location_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="אצווה לא נמצאה",
        )
    
    if batch.status == BatchStatus.SCRAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="אצווה כבר סומנה כגריטה",  # Batch already marked as scrap
        )
    
    batch.status = BatchStatus.SCRAP
    if reason:
        batch.notes = f"{batch.notes or ''}\nסיבת גריטה: {reason}".strip()
    
    await db.commit()
    await db.refresh(batch)
    
    response = BatchResponse.model_validate(batch)
    response.days_until_expiration = (batch.expiration_date - date.today()).days
    response.is_expired = batch.expiration_date < date.today()
    response.item_sku = batch.item.sku if batch.item else None
    response.item_name = batch.item.name if batch.item else None
    response.location_code = batch.location.location_code if batch.location else None
    
    return response


@router.put("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    batch_data: BatchUpdate,
    db: DbSession,
    current_user: WarehouseUser,
    scope: Scope,
) -> BatchResponse:
    """Update batch details"""
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .where(Batch.id == batch_id)
    )
    batch = result.scalar_one_or_none()

    if batch is None or (
        scope.location_ids is not None and batch.location_id not in scope.location_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="אצווה לא נמצאה",
        )

    # Optimistic-lock check: if the caller supplied the version it last
    # read, it must still match. Otherwise someone else updated this batch
    # in between and we'd silently clobber their change.
    if batch_data.version is not None and batch_data.version != batch.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="האצווה עודכנה על ידי משתמש אחר בינתיים, טען מחדש ונסה שוב",  # This batch was updated by someone else in the meantime, reload and try again
        )

    # Validate location if provided
    if batch_data.location_id:
        loc_result = await db.execute(
            select(Location).where(Location.id == batch_data.location_id)
        )
        if not loc_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="מיקום לא נמצא",  # Location not found
            )

    # Update fields (version is the lock token, not a persisted field to copy)
    update_data = batch_data.model_dump(exclude_unset=True, exclude={"version"})
    for field, value in update_data.items():
        setattr(batch, field, value)

    batch.version += 1  # Optimistic locking

    await db.commit()

    # Re-fetch with item/location eager-loaded instead of db.refresh(),
    # which expires relationships without reloading them - the next access
    # to batch.item (e.g. via the inventory_value property below) would
    # then trigger an async lazy-load outside a greenlet and raise
    # MissingGreenlet.
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .where(Batch.id == batch_id)
    )
    batch = result.scalar_one()

    response = BatchResponse.model_validate(batch)
    response.days_until_expiration = (batch.expiration_date - date.today()).days
    response.is_expired = batch.expiration_date < date.today()
    response.inventory_value = batch.quantity_available * (batch.item.cost_price if batch.item else 0)
    response.item_sku = batch.item.sku if batch.item else None
    response.item_name = batch.item.name if batch.item else None
    response.location_code = batch.location.location_code if batch.location else None
    
    return response


@router.get("/export/excel")
async def export_batches_excel(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> StreamingResponse:
    """Export all batches to Excel"""
    query = (
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .order_by(Batch.expiration_date)
    )
    location_clause = batch_location_filter(scope)
    if location_clause is not None:
        query = query.where(location_clause)
    result = await db.execute(query)
    batches = result.scalars().all()

    return export_service.export_batches_excel(list(batches))


@router.get("/export/csv")
async def export_batches_csv(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> StreamingResponse:
    """Export all batches to CSV"""
    query = (
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .order_by(Batch.expiration_date)
    )
    location_clause = batch_location_filter(scope)
    if location_clause is not None:
        query = query.where(location_clause)
    result = await db.execute(query)
    batches = result.scalars().all()

    return export_service.export_batches_csv(list(batches))


