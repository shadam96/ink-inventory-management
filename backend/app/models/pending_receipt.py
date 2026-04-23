"""Pending receipt queue — shared in-progress list of items to receive"""
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.location import Location
    from app.models.user import User


class PendingReceiptItem(BaseModel):
    """An item queued for receipt.

    A single global queue shared across all warehouse users. Rows are created
    by any user as they scan/enter incoming goods, and are drained together
    when someone clicks "Receive All" — at which point each row is converted
    into a real Batch + Movement and the pending rows are deleted.
    """

    __tablename__ = "pending_receipt_items"

    # What is being received
    item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    manufacturing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Optional identifiers (same semantics as on Batch)
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supplier_batch_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Who added this row (for the "Added by Alice" badge)
    added_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Relationships
    item: Mapped["Item"] = relationship("Item")
    location: Mapped[Optional["Location"]] = relationship("Location")
    added_by: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<PendingReceiptItem item={self.item_id} qty={self.quantity}>"
