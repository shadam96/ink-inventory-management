"""Customer model for delivery management"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.delivery_note import DeliveryNote


class Customer(BaseModel):
    """Customer model for delivery notes and consignment tracking"""
    
    __tablename__ = "customers"
    
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    contact_person: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    # VMI (Vendor Managed Inventory) settings
    is_vmi_customer: Mapped[bool] = mapped_column(
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
    delivery_notes: Mapped[List["DeliveryNote"]] = relationship(
        "DeliveryNote",
        back_populates="customer",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Customer {self.name}>"


