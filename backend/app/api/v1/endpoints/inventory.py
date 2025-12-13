"""Item/Inventory endpoints"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, ManagerUser
from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ItemResponse])
async def list_items(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    supplier: Optional[str] = None,
    below_reorder: Optional[bool] = None,
) -> PaginatedResponse[ItemResponse]:
    """List all items with pagination and filters"""
    query = select(Item).options(selectinload(Item.batches))
    
    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Item.sku.ilike(search_filter)) |
            (Item.name.ilike(search_filter))
        )
    
    if supplier:
        query = query.where(Item.supplier.ilike(f"%{supplier}%"))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Convert to response with computed fields
    item_responses = []
    for item in items:
        response = ItemResponse.model_validate(item)
        # Calculate computed fields
        active_batches = [b for b in item.batches if b.status == BatchStatus.ACTIVE]
        response.total_quantity_available = sum(b.quantity_available for b in active_batches)
        response.total_inventory_value = response.total_quantity_available * item.cost_price
        response.active_batches_count = len(active_batches)
        response.is_below_reorder_point = response.total_quantity_available < item.reorder_point
        
        # Filter by below_reorder if specified
        if below_reorder is not None:
            if below_reorder == response.is_below_reorder_point:
                item_responses.append(response)
        else:
            item_responses.append(response)
    
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
) -> ItemResponse:
    """Get item by ID"""
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.batches))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="פריט לא נמצא",  # Item not found
        )
    
    response = ItemResponse.model_validate(item)
    active_batches = [b for b in item.batches if b.status == BatchStatus.ACTIVE]
    response.total_quantity_available = sum(b.quantity_available for b in active_batches)
    response.total_inventory_value = response.total_quantity_available * item.cost_price
    response.active_batches_count = len(active_batches)
    response.is_below_reorder_point = response.total_quantity_available < item.reorder_point
    
    return response


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
    
    response = ItemResponse.model_validate(item)
    active_batches = [b for b in item.batches if b.status == BatchStatus.ACTIVE]
    response.total_quantity_available = sum(b.quantity_available for b in active_batches)
    response.total_inventory_value = response.total_quantity_available * item.cost_price
    response.active_batches_count = len(active_batches)
    response.is_below_reorder_point = response.total_quantity_available < item.reorder_point
    
    return response


@router.delete("/{item_id}", response_model=MessageResponse)
async def delete_item(
    item_id: UUID,
    db: DbSession,
    current_user: ManagerUser,
) -> MessageResponse:
    """Delete an item (only if no active batches)"""
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
    
    # Check for active batches
    active_batches = [b for b in item.batches if b.status == BatchStatus.ACTIVE]
    if active_batches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"לא ניתן למחוק פריט עם {len(active_batches)} אצוות פעילות",  # Cannot delete item with active batches
        )
    
    await db.delete(item)
    await db.commit()
    
    return MessageResponse(
        message=f"פריט {item.sku} נמחק בהצלחה",  # Item deleted successfully
        success=True,
    )


