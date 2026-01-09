"""Item (Ink) model for inventory management"""
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.batch import Batch
    from app.models.delivery_note import DeliveryNoteItem


class Item(BaseModel):
    """Ink item model - represents a type of ink product"""
    
    __tablename__ = "items"
    
    sku: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    supplier: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    unit_of_measure: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="KG"  # Common: KG, L, Units
    )
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="ILS"
    )
    reorder_point: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10
    )
    min_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5
    )
    max_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100
    )
    
    # Relationships
    batches: Mapped[List["Batch"]] = relationship(
        "Batch",
        back_populates="item",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    delivery_note_items: Mapped[List["DeliveryNoteItem"]] = relationship(
        "DeliveryNoteItem",
        back_populates="item",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Item {self.sku}: {self.name}>"
    
    @property
    def total_quantity_available(self) -> Decimal:
        """Calculate total available quantity across all active batches"""
        return sum(
            batch.quantity_available
            for batch in self.batches
            if batch.status == "active"
        )
    
    @property
    def total_inventory_value(self) -> Decimal:
        """Calculate total inventory value"""
        return self.total_quantity_available * self.cost_price
    
    @property
    def is_below_reorder_point(self) -> bool:
        """Check if item needs reordering"""
        return self.total_quantity_available < self.reorder_point
    
    @property
    def active_batches_count(self) -> int:
        """Count of active batches"""
        return len([b for b in self.batches if b.status == "active"])


