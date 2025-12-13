"""Batch endpoints with FEFO support"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, WarehouseUser
from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.location import Location
from app.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[BatchResponse])
async def list_batches(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: Optional[UUID] = None,
    status_filter: Optional[BatchStatus] = None,
    expiring_within_days: Optional[int] = None,
    sort_by_expiration: bool = True,
) -> PaginatedResponse[BatchResponse]:
    """List batches with FEFO sorting by default"""
    query = (
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
    )
    
    # Apply filters
    if item_id:
        query = query.where(Batch.item_id == item_id)
    
    if status_filter:
        query = query.where(Batch.status == status_filter)
    else:
        # By default, show only active batches
        query = query.where(Batch.status == BatchStatus.ACTIVE)
    
    if expiring_within_days:
        expiration_threshold = date.today()
        from datetime import timedelta
        expiration_threshold = date.today() + timedelta(days=expiring_within_days)
        query = query.where(Batch.expiration_date <= expiration_threshold)
    
    # FEFO sorting (First Expired, First Out)
    if sort_by_expiration:
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
    current_user: CurrentUser,
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
    current_user: CurrentUser,
) -> BatchResponse:
    """Get batch by ID"""
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .where(Batch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    
    if batch is None:
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
    reason: Optional[str] = None,
) -> BatchResponse:
    """Mark a batch as scrap (גריטה)"""
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .where(Batch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    
    if batch is None:
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
) -> BatchResponse:
    """Update batch details"""
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.item), selectinload(Batch.location))
        .where(Batch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="אצווה לא נמצאה",
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
    
    # Update fields
    update_data = batch_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(batch, field, value)
    
    batch.version += 1  # Optimistic locking
    
    await db.commit()
    await db.refresh(batch)
    
    response = BatchResponse.model_validate(batch)
    response.days_until_expiration = (batch.expiration_date - date.today()).days
    response.is_expired = batch.expiration_date < date.today()
    response.inventory_value = batch.quantity_available * (batch.item.cost_price if batch.item else 0)
    response.item_sku = batch.item.sku if batch.item else None
    response.item_name = batch.item.name if batch.item else None
    response.location_code = batch.location.location_code if batch.location else None
    
    return response


