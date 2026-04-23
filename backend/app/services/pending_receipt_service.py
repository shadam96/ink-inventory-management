"""Service layer for the shared pending-receipt queue"""
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item import Item
from app.models.pending_receipt import PendingReceiptItem
from app.services.receiving_service import ReceivingService


class PendingReceiptService:
    """Operations on the global pending-receipt queue.

    All rows are visible to, and mutable by, any warehouse user. Receiving
    works by draining the queue — converting each pending row into a real
    Batch + Movement via the existing ReceivingService.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_pending(self) -> List[PendingReceiptItem]:
        """Return every pending row, oldest first, with item + adder loaded."""
        result = await self.db.execute(
            select(PendingReceiptItem)
            .options(
                selectinload(PendingReceiptItem.item),
                selectinload(PendingReceiptItem.added_by),
            )
            .order_by(PendingReceiptItem.created_at.asc())
        )
        return list(result.scalars().all())

    async def add(
        self,
        *,
        user_id: UUID,
        item_id: UUID,
        quantity: Decimal,
        expiration_date: date,
        manufacturing_date: Optional[date] = None,
        batch_number: Optional[str] = None,
        supplier_batch_number: Optional[str] = None,
        location_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> PendingReceiptItem:
        """Add one row. Validates item existence and expiration date.

        Uniqueness of batch_number is NOT enforced here — the queue is a
        staging area; the real uniqueness check happens in ReceivingService
        at drain time.
        """
        # Delegate cheap validations to ReceivingService so rules stay in one place
        rs = ReceivingService(self.db)
        await rs.validate_item(item_id)
        if location_id:
            await rs.validate_location(location_id)
        if expiration_date < date.today():
            raise ValueError("תאריך תפוגה לא יכול להיות בעבר")
        if quantity <= 0:
            raise ValueError("כמות חייבת להיות חיובית")

        row = PendingReceiptItem(
            item_id=item_id,
            quantity=quantity,
            expiration_date=expiration_date,
            manufacturing_date=manufacturing_date,
            batch_number=batch_number or None,
            supplier_batch_number=supplier_batch_number or None,
            location_id=location_id,
            notes=notes or None,
            added_by_user_id=user_id,
        )
        self.db.add(row)
        await self.db.flush()

        # Reload with relationships so callers can serialise immediately
        result = await self.db.execute(
            select(PendingReceiptItem)
            .where(PendingReceiptItem.id == row.id)
            .options(
                selectinload(PendingReceiptItem.item),
                selectinload(PendingReceiptItem.added_by),
            )
        )
        return result.scalar_one()

    async def remove(self, pending_id: UUID) -> bool:
        """Delete one pending row. Returns True if it existed, False otherwise."""
        result = await self.db.execute(
            select(PendingReceiptItem).where(PendingReceiptItem.id == pending_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.db.delete(row)
        await self.db.flush()
        return True

    async def drain_and_receive(self, user_id: UUID) -> tuple[list, list, str, list]:
        """Convert every pending row into a Batch + Movement under a single GRN.

        Returns (batches, movements, grn_number, warnings). Empties the queue
        on success. Raises ValueError if the queue is empty or any row fails
        validation — in which case the caller should rollback.
        """
        pending = await self.list_pending()
        if not pending:
            raise ValueError("אין פריטים ברשימת ההמתנה")  # Pending queue is empty

        receipts = [
            {
                "item_id": p.item_id,
                "quantity": p.quantity,
                "expiration_date": p.expiration_date,
                "manufacturing_date": p.manufacturing_date,
                "batch_number": p.batch_number,
                "supplier_batch_number": p.supplier_batch_number,
                "location_id": p.location_id,
                "notes": p.notes,
            }
            for p in pending
        ]

        rs = ReceivingService(self.db)
        batches, movements, grn_number = await rs.receive_multiple(
            receipts=receipts,
            user_id=user_id,
        )

        warnings: list[dict] = []
        for batch in batches:
            info = await rs.record_short_expiry_alert(batch)
            if info is not None:
                warnings.append(info)

        for row in pending:
            await self.db.delete(row)
        await self.db.flush()

        return batches, movements, grn_number, warnings


def serialize_pending(row: PendingReceiptItem) -> dict:
    """Shape a PendingReceiptItem for WebSocket + HTTP response payloads."""
    user = row.added_by
    item = row.item
    return {
        "id": str(row.id),
        "item_id": str(row.item_id),
        "quantity": str(row.quantity),
        "expiration_date": row.expiration_date.isoformat(),
        "manufacturing_date": row.manufacturing_date.isoformat() if row.manufacturing_date else None,
        "batch_number": row.batch_number,
        "supplier_batch_number": row.supplier_batch_number,
        "location_id": str(row.location_id) if row.location_id else None,
        "notes": row.notes,
        "added_by_user_id": str(row.added_by_user_id),
        "added_by_username": user.username if user else "",
        "added_by_full_name": user.full_name if user else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "item_sku": item.sku if item else "",
        "item_name": item.name if item else "",
    }
