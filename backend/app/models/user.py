"""User model for authentication and authorization"""
import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.movement import Movement
    from app.models.delivery_note import DeliveryNote


class UserRole(str, enum.Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    MANAGER = "manager"
    WAREHOUSE_WORKER = "warehouse_worker"
    VIEWER = "viewer"
    CUSTOMER = "customer"


class User(BaseModel):
    """User model for authentication and RBAC"""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.VIEWER,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    notification_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default=None
    )
    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default="false"
    )
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True
    )
    # Login lockout - defends /auth/login against unlimited password
    # guessing. failed_login_attempts resets to 0 on any successful login;
    # locked_until is set once the threshold is hit and cleared on success.
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        lazy="selectin"
    )
    movements: Mapped[List["Movement"]] = relationship(
        "Movement",
        back_populates="user",
        lazy="selectin"
    )
    delivery_notes: Mapped[List["DeliveryNote"]] = relationship(
        "DeliveryNote",
        back_populates="created_by_user",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_manager(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.MANAGER)

    @property
    def is_customer(self) -> bool:
        return self.role == UserRole.CUSTOMER

    @property
    def can_modify_inventory(self) -> bool:
        return self.role in (
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.WAREHOUSE_WORKER
        )


