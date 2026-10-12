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
from app.services.expiration_classifier import classify_expiration


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
        
        # Categorize by expiration, using the same 30/60/90-day boundaries
        # as fefo_engine.py and dashboard_service.py. Already-expired
        # batches (classify_expiration -> "expired") are intentionally
        # excluded from all four buckets here, matching this method's
        # existing (pre-refactor) behavior.
        today = date.today()
        breakdown = {"critical": Decimal("0"), "warning": Decimal("0"), "caution": Decimal("0"), "safe": Decimal("0")}
        for b in active_batches:
            level = classify_expiration((b.expiration_date - today).days)
            if level in breakdown:
                breakdown[level] += b.quantity_available

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
                "critical_30_days": breakdown["critical"],
                "warning_60_days": breakdown["warning"],
                "caution_90_days": breakdown["caution"],
                "safe": breakdown["safe"],
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

        # ADJUSTMENT is the only movement type allowed to carry a negative
        # (or zero) quantity - it represents a signed delta from a physical
        # count. Every other type represents a physical quantity of stock
        # moving in one direction, so a non-positive value here is always
        # invalid: a negative DISPATCH/CONSUMPTION/SCRAP would otherwise
        # *increase* quantity_available (quantity_before - negative), while
        # the stored Movement.quantity uses abs(quantity), masking the sign
        # inversion from the audit trail. This is a defense-in-depth check;
        # the HTTP layer (Pydantic Field(gt=0)) already guards this for
        # requests that go through the picking/receiving endpoints, but
        # this service function can also be called directly.
        if movement_type != MovementType.ADJUSTMENT and quantity <= 0:
            raise ValueError("כמות חייבת להיות חיובית")  # Quantity must be positive

        quantity_before = batch.quantity_available

        # Calculate new quantity based on movement type
        if movement_type in (MovementType.RECEIPT,):
            quantity_after = quantity_before + quantity
        elif movement_type in (MovementType.DISPATCH, MovementType.CONSUMPTION, MovementType.SCRAP):
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
        # Lock the row here (not just inside record_movement) so the delta
        # below is computed from the same value record_movement will see.
        # Without this lock, a concurrent movement on this batch between
        # this read and record_movement's own locked re-read could change
        # quantity_available in between, and record_movement would apply
        # this stale delta on top of the *new* value - producing a final
        # quantity that doesn't match the caller's intended new_quantity.
        result = await self.db.execute(
            select(Batch).where(Batch.id == batch_id).with_for_update()
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
        location_ids: Optional[List[UUID]] = None,
    ) -> List[Movement]:
        """Get movement history with filters.

        location_ids restricts to movements whose batch currently sits at
        one of those locations (used for staff location-scoping) - None
        means unrestricted.
        """
        query = (
            select(Movement)
            .options(
                selectinload(Movement.batch).selectinload(Batch.item),
                selectinload(Movement.user)
            )
            .order_by(Movement.timestamp.desc())
        )

        joined_batch = False

        if batch_id:
            query = query.where(Movement.batch_id == batch_id)

        if item_id:
            query = query.join(Batch).where(Batch.item_id == item_id)
            joined_batch = True

        if location_ids is not None:
            if not joined_batch:
                query = query.join(Batch)
            query = query.where(Batch.location_id.in_(location_ids))

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

