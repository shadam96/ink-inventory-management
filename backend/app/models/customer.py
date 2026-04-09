"""Customer model for delivery management"""
import uuid
from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
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
    phone_primary: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    phone_secondary: Mapped[Optional[str]] = mapped_column(
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
    machines: Mapped[List["CustomerMachine"]] = relationship(
        "CustomerMachine",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Customer {self.name}>"


class CustomerMachine(BaseModel):
    """A machine in a customer's possession.

    Only the minimum fields are populated for now; additional fields
    (serial number, model, maintenance schedule, etc.) can be added
    later without breaking this schema.
    """

    __tablename__ = "customer_machines"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    machine_type: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    installation_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="machines",
    )

    def __repr__(self) -> str:
        return f"<CustomerMachine {self.machine_type}>"


