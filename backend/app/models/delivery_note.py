"""Delivery note models for dispatch documentation"""
import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.user import User
    from app.models.item import Item
    from app.models.batch import Batch


class DeliveryNoteStatus(str, enum.Enum):
    """Delivery note status"""
    DRAFT = "draft"
    ISSUED = "issued"
    DELIVERED = "delivered"
    INVOICED = "invoiced"
    CANCELLED = "cancelled"


class DeliveryNote(BaseModel):
    """Delivery note (תעודת משלוח) model"""
    
    __tablename__ = "delivery_notes"
    
    # Foreign keys
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # Document identification
    delivery_note_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    
    # Status and dates
    status: Mapped[DeliveryNoteStatus] = mapped_column(
        Enum(DeliveryNoteStatus),
        default=DeliveryNoteStatus.DRAFT,
        nullable=False,
        index=True
    )
    issue_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )
    delivery_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )
    
    # Consignment flag
    is_consignment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="delivery_notes"
    )
    created_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="delivery_notes"
    )
    items: Mapped[List["DeliveryNoteItem"]] = relationship(
        "DeliveryNoteItem",
        back_populates="delivery_note",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<DeliveryNote {self.delivery_note_number}>"
    
    @staticmethod
    def generate_delivery_note_number(sequence: int) -> str:
        """Generate delivery note number: DN-YYMMDD-XXXX"""
        from datetime import datetime
        date_str = datetime.now().strftime("%y%m%d")
        return f"DN-{date_str}-{sequence:04d}"
    
    @property
    def total_quantity(self) -> Decimal:
        """Calculate total quantity in delivery note"""
        return sum(item.quantity for item in self.items)
    
    @property
    def items_count(self) -> int:
        """Number of line items"""
        return len(self.items)


class DeliveryNoteItem(BaseModel):
    """Line item in delivery note"""
    
    __tablename__ = "delivery_note_items"
    
    # Foreign keys
    delivery_note_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("delivery_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False
    )
    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # Quantity
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )
    
    # Relationships
    delivery_note: Mapped["DeliveryNote"] = relationship(
        "DeliveryNote",
        back_populates="items"
    )
    item: Mapped["Item"] = relationship(
        "Item",
        back_populates="delivery_note_items"
    )
    batch: Mapped["Batch"] = relationship(
        "Batch",
        back_populates="delivery_note_items"
    )
    
    def __repr__(self) -> str:
        return f"<DeliveryNoteItem {self.quantity}>"


