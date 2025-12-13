"""User model for authentication and authorization"""
import enum
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.movement import Movement
    from app.models.delivery_note import DeliveryNote


class UserRole(str, enum.Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    MANAGER = "manager"
    WAREHOUSE_WORKER = "warehouse_worker"
    VIEWER = "viewer"


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
    
    # Relationships
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
    def can_modify_inventory(self) -> bool:
        return self.role in (
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.WAREHOUSE_WORKER
        )


