"""Batch model for tracking ink batches with expiration dates"""
import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.location import Location
    from app.models.movement import Movement
    from app.models.delivery_note import DeliveryNoteItem


class BatchStatus(str, enum.Enum):
    """Batch status enum"""
    ACTIVE = "active"
    SCRAP = "scrap"
    DEPLETED = "depleted"


class Batch(BaseModel):
    """Ink batch model with FEFO tracking"""
    
    __tablename__ = "batches"
    __table_args__ = (
        CheckConstraint(
            "expiration_date >= receipt_date",
            name="check_expiration_after_receipt"
        ),
        CheckConstraint(
            "quantity_available >= 0",
            name="check_quantity_non_negative"
        ),
        Index("ix_batches_expiration_status", "expiration_date", "status"),
        Index("ix_batches_item_status", "item_id", "status"),
    )
    
    # Foreign keys
    item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    location_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Batch identification
    batch_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    supplier_batch_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # Quantities
    quantity_received: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )
    quantity_available: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )
    
    # Dates
    receipt_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )
    expiration_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    
    # Status
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus),
        default=BatchStatus.ACTIVE,
        nullable=False,
        index=True
    )
    
    # Optional notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Version for optimistic locking
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    
    # Relationships
    item: Mapped["Item"] = relationship(
        "Item",
        back_populates="batches"
    )
    location: Mapped[Optional["Location"]] = relationship(
        "Location",
        back_populates="batches"
    )
    movements: Mapped[List["Movement"]] = relationship(
        "Movement",
        back_populates="batch",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    delivery_note_items: Mapped[List["DeliveryNoteItem"]] = relationship(
        "DeliveryNoteItem",
        back_populates="batch",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Batch {self.batch_number}>"
    
    @staticmethod
    def generate_batch_number(prefix: str = "GR") -> str:
        """Generate auto batch number: GR-YYMMDD-XXX"""
        from datetime import datetime
        import random
        date_str = datetime.now().strftime("%y%m%d")
        random_suffix = str(random.randint(100, 999))
        return f"{prefix}-{date_str}-{random_suffix}"
    
    @property
    def is_expired(self) -> bool:
        """Check if batch is expired"""
        return self.expiration_date < date.today()
    
    @property
    def days_until_expiration(self) -> int:
        """Days until expiration (negative if expired)"""
        return (self.expiration_date - date.today()).days
    
    @property
    def inventory_value(self) -> Decimal:
        """Calculate batch inventory value"""
        return self.quantity_available * (self.item.cost_price if self.item else Decimal("0"))
    
    @property
    def is_depleted(self) -> bool:
        """Check if batch is depleted"""
        return self.quantity_available <= 0
    
    def can_pick(self, quantity: Decimal) -> bool:
        """Check if quantity can be picked from this batch"""
        return (
            self.status == BatchStatus.ACTIVE
            and not self.is_expired
            and self.quantity_available >= quantity
        )


