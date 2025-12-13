"""Inventory service for stock management operations"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.movement import Movement, MovementType
from app.models.user import User


class InventoryService:
    """Service for inventory management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_item_stock_summary(self, item_id: UUID) -> dict:
        """Get stock summary for an item"""
        result = await self.db.execute(
            select(Item)
            .options(selectinload(Item.batches))
            .where(Item.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            return None
        
        active_batches = [b for b in item.batches if b.status == BatchStatus.ACTIVE]
        
        total_quantity = sum(b.quantity_available for b in active_batches)
        total_value = total_quantity * item.cost_price
        
        # Categorize by expiration
        today = date.today()
        expiring_30 = sum(
            b.quantity_available for b in active_batches
            if 0 <= (b.expiration_date - today).days <= 30
        )
        expiring_60 = sum(
            b.quantity_available for b in active_batches
            if 30 < (b.expiration_date - today).days <= 60
        )
        expiring_90 = sum(
            b.quantity_available for b in active_batches
            if 60 < (b.expiration_date - today).days <= 90
        )
        safe = sum(
            b.quantity_available for b in active_batches
            if (b.expiration_date - today).days > 90
        )
        
        return {
            "item_id": item.id,
            "sku": item.sku,
            "name": item.name,
            "total_quantity": total_quantity,
            "total_value": total_value,
            "unit_of_measure": item.unit_of_measure,
            "batches_count": len(active_batches),
            "is_below_reorder": total_quantity < item.reorder_point,
            "expiration_breakdown": {
                "critical_30_days": expiring_30,
                "warning_60_days": expiring_60,
                "caution_90_days": expiring_90,
                "safe": safe,
            }
        }
    
    async def record_movement(
        self,
        batch_id: UUID,
        movement_type: MovementType,
        quantity: Decimal,
        user_id: UUID,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Movement:
        """Record an inventory movement (audit trail)"""
        # Get batch with lock for update
        result = await self.db.execute(
            select(Batch).where(Batch.id == batch_id).with_for_update()
        )
        batch = result.scalar_one_or_none()
        
        if not batch:
            raise ValueError(f"אצווה {batch_id} לא נמצאה")  # Batch not found
        
        quantity_before = batch.quantity_available
        
        # Calculate new quantity based on movement type
        if movement_type in (MovementType.RECEIPT,):
            quantity_after = quantity_before + quantity
        elif movement_type in (MovementType.DISPATCH, MovementType.SCRAP):
            if quantity > quantity_before:
                raise ValueError(
                    f"כמות לא מספיקה. זמין: {quantity_before}, נדרש: {quantity}"
                )
            quantity_after = quantity_before - quantity
        elif movement_type == MovementType.ADJUSTMENT:
            # Adjustment can be positive or negative
            quantity_after = quantity_before + quantity
            if quantity_after < 0:
                raise ValueError("כמות לא יכולה להיות שלילית")
        else:
            quantity_after = quantity_before
        
        # Update batch quantity
        batch.quantity_available = quantity_after
        batch.version += 1
        
        # Check if depleted
        if batch.quantity_available <= 0:
            batch.status = BatchStatus.DEPLETED
        
        # Create movement record
        movement = Movement(
            batch_id=batch_id,
            user_id=user_id,
            movement_type=movement_type,
            quantity=abs(quantity),
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reference_number=reference_number,
            notes=notes,
            timestamp=datetime.now(timezone.utc),
        )
        
        self.db.add(movement)
        await self.db.flush()
        
        return movement
    
    async def adjust_quantity(
        self,
        batch_id: UUID,
        new_quantity: Decimal,
        user_id: UUID,
        reason: str,
    ) -> Movement:
        """Adjust batch quantity (e.g., after physical count)"""
        result = await self.db.execute(
            select(Batch).where(Batch.id == batch_id)
        )
        batch = result.scalar_one_or_none()
        
        if not batch:
            raise ValueError(f"אצווה {batch_id} לא נמצאה")
        
        adjustment = new_quantity - batch.quantity_available
        
        return await self.record_movement(
            batch_id=batch_id,
            movement_type=MovementType.ADJUSTMENT,
            quantity=adjustment,
            user_id=user_id,
            notes=f"התאמת מלאי: {reason}",
        )
    
    async def get_movements_history(
        self,
        batch_id: Optional[UUID] = None,
        item_id: Optional[UUID] = None,
        movement_type: Optional[MovementType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> List[Movement]:
        """Get movement history with filters"""
        query = (
            select(Movement)
            .options(
                selectinload(Movement.batch).selectinload(Batch.item),
                selectinload(Movement.user)
            )
            .order_by(Movement.timestamp.desc())
        )
        
        if batch_id:
            query = query.where(Movement.batch_id == batch_id)
        
        if item_id:
            query = query.join(Batch).where(Batch.item_id == item_id)
        
        if movement_type:
            query = query.where(Movement.movement_type == movement_type)
        
        if start_date:
            query = query.where(func.date(Movement.timestamp) >= start_date)
        
        if end_date:
            query = query.where(func.date(Movement.timestamp) <= end_date)
        
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def check_and_mark_expired(self) -> List[Batch]:
        """Check for expired batches and mark them as scrap"""
        today = date.today()
        
        result = await self.db.execute(
            select(Batch)
            .where(
                Batch.status == BatchStatus.ACTIVE,
                Batch.expiration_date < today,
            )
        )
        expired_batches = list(result.scalars().all())
        
        for batch in expired_batches:
            batch.status = BatchStatus.SCRAP
            batch.notes = f"{batch.notes or ''}\nסומן כגריטה אוטומטית עקב פג תוקף: {today}".strip()
        
        await self.db.flush()
        return expired_batches

