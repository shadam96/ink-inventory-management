"""Movement model for tracking inventory changes (audit trail)"""
import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.batch import Batch
    from app.models.user import User


class MovementType(str, enum.Enum):
    """Types of inventory movements"""
    RECEIPT = "receipt"
    DISPATCH = "dispatch"
    ADJUSTMENT = "adjustment"
    SCRAP = "scrap"
    TRANSFER = "transfer"


class Movement(BaseModel):
    """Inventory movement model for complete audit trail"""
    
    __tablename__ = "movements"
    
    # Foreign keys
    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Movement details
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType),
        nullable=False,
        index=True
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )
    
    # Before/After for audit
    quantity_before: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )
    quantity_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )
    
    # Reference documents
    reference_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    
    # Timestamp (separate from created_at for explicit movement time)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Relationships
    batch: Mapped["Batch"] = relationship(
        "Batch",
        back_populates="movements"
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="movements"
    )
    
    def __repr__(self) -> str:
        return f"<Movement {self.movement_type.value}: {self.quantity}>"
    
    @property
    def is_inbound(self) -> bool:
        """Check if movement adds inventory"""
        return self.movement_type in (MovementType.RECEIPT, MovementType.ADJUSTMENT)
    
    @property
    def is_outbound(self) -> bool:
        """Check if movement removes inventory"""
        return self.movement_type in (
            MovementType.DISPATCH,
            MovementType.SCRAP,
            MovementType.TRANSFER
        )


