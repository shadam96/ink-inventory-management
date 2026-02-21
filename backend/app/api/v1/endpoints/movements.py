"""Movement history and audit trail endpoints"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.movement import MovementType, Movement
from app.models.batch import Batch
from app.services.inventory_service import InventoryService
from app.services.export_service import export_service
from app.schemas.movement import MovementResponse

router = APIRouter()


class MovementHistoryResponse(BaseModel):
    """Response containing movement history"""
    movements: List[dict]
    total: int


@router.get("", response_model=MovementHistoryResponse)
async def get_movement_history(
    db: DbSession,
    current_user: CurrentUser,
    batch_id: Optional[UUID] = None,
    item_id: Optional[UUID] = None,
    movement_type: Optional[MovementType] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(100, ge=1, le=500),
) -> MovementHistoryResponse:
    """
    Get movement history with optional filters.
    
    Provides audit trail for inventory changes.
    """
    service = InventoryService(db)
    
    movements = await service.get_movements_history(
        batch_id=batch_id,
        item_id=item_id,
        movement_type=movement_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    
    # Convert to response format
    movements_data = []
    for m in movements:
        movements_data.append({
            "id": str(m.id),
            "batch_id": str(m.batch_id),
            "batch_number": m.batch.batch_number if m.batch else None,
            "item_sku": m.batch.item.sku if m.batch and m.batch.item else None,
            "item_name": m.batch.item.name if m.batch and m.batch.item else None,
            "user_id": str(m.user_id),
            "user_name": m.user.full_name if m.user else None,
            "movement_type": m.movement_type.value,
            "quantity": float(m.quantity),
            "quantity_before": float(m.quantity_before),
            "quantity_after": float(m.quantity_after),
            "reference_number": m.reference_number,
            "timestamp": m.timestamp.isoformat(),
            "notes": m.notes,
        })
    
    return MovementHistoryResponse(
        movements=movements_data,
        total=len(movements_data),
    )


@router.get("/by-batch/{batch_id}")
async def get_batch_movements(
    batch_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Get all movements for a specific batch"""
    service = InventoryService(db)
    
    movements = await service.get_movements_history(
        batch_id=batch_id,
        limit=limit,
    )
    
    movements_data = []
    for m in movements:
        movements_data.append({
            "id": str(m.id),
            "movement_type": m.movement_type.value,
            "quantity": float(m.quantity),
            "quantity_before": float(m.quantity_before),
            "quantity_after": float(m.quantity_after),
            "reference_number": m.reference_number,
            "timestamp": m.timestamp.isoformat(),
            "user_name": m.user.full_name if m.user else None,
            "notes": m.notes,
        })
    
    return {
        "batch_id": str(batch_id),
        "movements": movements_data,
        "total": len(movements_data),
    }


@router.get("/by-item/{item_id}")
async def get_item_movements(
    item_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Get all movements for a specific item across all batches"""
    service = InventoryService(db)
    
    movements = await service.get_movements_history(
        item_id=item_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    
    # Calculate summary
    total_received = sum(
        m.quantity for m in movements if m.movement_type == MovementType.RECEIPT
    )
    total_dispatched = sum(
        m.quantity for m in movements if m.movement_type == MovementType.DISPATCH
    )
    total_scrapped = sum(
        m.quantity for m in movements if m.movement_type == MovementType.SCRAP
    )
    
    movements_data = []
    for m in movements:
        movements_data.append({
            "id": str(m.id),
            "batch_id": str(m.batch_id),
            "batch_number": m.batch.batch_number if m.batch else None,
            "movement_type": m.movement_type.value,
            "quantity": float(m.quantity),
            "quantity_before": float(m.quantity_before),
            "quantity_after": float(m.quantity_after),
            "reference_number": m.reference_number,
            "timestamp": m.timestamp.isoformat(),
            "user_name": m.user.full_name if m.user else None,
            "notes": m.notes,
        })
    
    return {
        "item_id": str(item_id),
        "summary": {
            "total_received": float(total_received),
            "total_dispatched": float(total_dispatched),
            "total_scrapped": float(total_scrapped),
        },
        "movements": movements_data,
        "total": len(movements_data),
    }


@router.get("/export/excel")
async def export_movements_excel(
    db: DbSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Export all movements to Excel"""
    query = (
        select(Movement)
        .options(
            selectinload(Movement.batch).selectinload(Batch.item),
            selectinload(Movement.user)
        )
        .order_by(Movement.timestamp.desc())
        .limit(1000)  # Limit to prevent huge exports
    )
    result = await db.execute(query)
    movements = result.scalars().all()
    
    return export_service.export_movements_excel(list(movements))


@router.get("/export/csv")
async def export_movements_csv(
    db: DbSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Export all movements to CSV"""
    query = (
        select(Movement)
        .options(
            selectinload(Movement.batch).selectinload(Batch.item),
            selectinload(Movement.user)
        )
        .order_by(Movement.timestamp.desc())
        .limit(1000)  # Limit to prevent huge exports
    )
    result = await db.execute(query)
    movements = result.scalars().all()
    
    return export_service.export_movements_csv(list(movements))

