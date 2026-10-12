"""Item/Inventory endpoints"""
from datetime import date
from typing import Literal, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import AccessScope, CurrentUser, DbSession, ManagerUser, Scope, StaffUser
from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from app.models.user import User, UserRole
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.export_service import export_service
from app.services.scoping import batch_access_filter

router = APIRouter()


def _scoped_batches_loader(current_user: User, scope: AccessScope):
    """selectinload(Item.batches), limited to the batches this user may see
    (a customer's delivered stock, or a scoped staff user's locations), so
    the stock fields below agree with what picking suggests."""
    clause = batch_access_filter(current_user, scope)
    if clause is None:
        return selectinload(Item.batches)
    return selectinload(Item.batches.and_(clause))


def _item_response(item: Item, current_user: User) -> ItemResponse:
    """ItemResponse with stock fields computed from the already-loaded
    item.batches. Customers never see cost."""
    response = ItemResponse.model_validate(item)
    # Expired batches keep ACTIVE status (there is no EXPIRED state) but
    # must not count as pickable stock, otherwise the picking screen sees an
    # item as "in stock" but the FEFO engine filters out every batch.
    today = date.today()
    pickable_batches = [
        b for b in item.batches
        if b.status == BatchStatus.ACTIVE and b.expiration_date >= today
    ]
    response.total_quantity_available = sum(b.quantity_available for b in pickable_batches)
    response.active_batches_count = len(pickable_batches)
    response.is_below_reorder_point = response.total_quantity_available < item.reorder_point
    if current_user.role == UserRole.CUSTOMER:
        response.cost_price = None
        # model_validate copied Item.total_inventory_value (a model property)
        response.total_inventory_value = None
    else:
        response.total_inventory_value = response.total_quantity_available * item.cost_price
    return response


@router.get("", response_model=PaginatedResponse[ItemResponse])
async def list_items(
    db: DbSession,
    current_user: CurrentUser,
    scope: Scope,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    supplier: Optional[str] = None,
    below_reorder: Optional[bool] = None,
    sort_by: Optional[Literal["sku", "name", "supplier", "cost_price", "reorder_point", "created_at"]] = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> PaginatedResponse[ItemResponse]:
    """List all items with pagination and filters"""
    query = select(Item).options(_scoped_batches_loader(current_user, scope))

    # Ordering by cost would still reveal it to a customer
    if sort_by == "cost_price" and current_user.role == UserRole.CUSTOMER:
        sort_by = None

    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Item.sku.ilike(search_filter)) |
            (Item.name.ilike(search_filter))
        )

    if supplier:
        query = query.where(Item.supplier.ilike(f"%{supplier}%"))

    # Filtered in SQL so total/pages and OFFSET/LIMIT agree with it. Stock is
    # what _item_response counts: active, unexpired, visible to this user.
    if below_reorder is not None:
        stock_where = [
            Batch.item_id == Item.id,
            Batch.status == BatchStatus.ACTIVE,
            Batch.expiration_date >= date.today(),
        ]
        access_clause = batch_access_filter(current_user, scope)
        if access_clause is not None:
            stock_where.append(access_clause)
        stock = (
            select(func.coalesce(func.sum(Batch.quantity_available), 0))
            .where(*stock_where)
            .correlate(Item)
            .scalar_subquery()
        )
        query = query.where(
            stock < Item.reorder_point if below_reorder else stock >= Item.reorder_point
        )

    # Apply sorting. Without a total order, Postgres may return OFFSET/LIMIT
    # pages in any order, so paging through could skip or repeat items -
    # default to name and always break ties by id.
    if sort_by:
        col = getattr(Item, sort_by)
        query = query.order_by(col.desc() if sort_order == "desc" else col.asc())
    else:
        query = query.order_by(Item.name)
    query = query.order_by(Item.id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Convert to response with computed fields
    item_responses = [_item_response(item, current_user) for item in items]

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return PaginatedResponse(
        items=item_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    db: DbSession,
    current_user: ManagerUser,
) -> ItemResponse:
    """Create a new inventory item"""
    # Check if SKU exists
    result = await db.execute(
        select(Item).where(Item.sku == item_data.sku)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"מק\"ט {item_data.sku} כבר קיים",  # SKU already exists
        )
    
    item = Item(**item_data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    response = ItemResponse.model_validate(item)
    response.total_quantity_available = 0
    response.total_inventory_value = 0
    response.active_batches_count = 0
    response.is_below_reorder_point = True
    
    return response


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    scope: Scope,
) -> ItemResponse:
    """Get item by ID"""
    result = await db.execute(
        select(Item)
        .options(_scoped_batches_loader(current_user, scope))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="פריט לא נמצא",  # Item not found
        )

    return _item_response(item, current_user)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: UUID,
    item_data: ItemUpdate,
    db: DbSession,
    current_user: ManagerUser,
) -> ItemResponse:
    """Update an item"""
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.batches))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="פריט לא נמצא",
        )
    
    # Check SKU uniqueness if changing
    if item_data.sku and item_data.sku != item.sku:
        result = await db.execute(
            select(Item).where(Item.sku == item_data.sku)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"מק\"ט {item_data.sku} כבר קיים",
            )
    
    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    await db.commit()
    await db.refresh(item)

    return _item_response(item, current_user)


@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_item(
    item_id: UUID,
    db: DbSession,
    current_user: ManagerUser,
) -> MessageResponse:
    """Delete an item (only if it has no batches at all - including
    depleted/expired ones, since those still carry historical Movement
    records that must not be silently destroyed)."""
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.batches))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="פריט לא נמצא",
        )

    # Block deletion if the item has ANY batches, not just active ones -
    # depleted/expired batches still carry historical Movement records.
    if item.batches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"לא ניתן למחוק פריט עם {len(item.batches)} אצוות (כולל היסטוריות)",  # Cannot delete item with batches (including historical ones)
        )
    
    await db.delete(item)
    await db.commit()
    
    return MessageResponse(
        message=f"פריט {item.sku} נמחק בהצלחה",  # Item deleted successfully
        success=True,
    )


@router.get("/export/excel")
async def export_items_excel(
    db: DbSession,
    current_user: StaffUser,
) -> StreamingResponse:
    """Export all items to Excel"""
    query = select(Item).order_by(Item.sku)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return export_service.export_items_excel(list(items))


@router.get("/export/csv")
async def export_items_csv(
    db: DbSession,
    current_user: StaffUser,
) -> StreamingResponse:
    """Export all items to CSV"""
    query = select(Item).order_by(Item.sku)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return export_service.export_items_csv(list(items))


