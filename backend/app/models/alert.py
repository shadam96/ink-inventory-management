"""Alert model for notifications and warnings"""
import enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AlertType(str, enum.Enum):
    """Types of alerts"""
    EXPIRATION_WARNING = "expiration_warning"
    EXPIRATION_CRITICAL = "expiration_critical"
    EXPIRED = "expired"
    LOW_STOCK = "low_stock"
    DEAD_STOCK = "dead_stock"
    REORDER_POINT = "reorder_point"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(BaseModel):
    """Alert model for system notifications"""
    
    __tablename__ = "alerts"
    
    # Alert classification
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType),
        nullable=False,
        index=True
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity),
        default=AlertSeverity.INFO,
        nullable=False,
        index=True
    )
    
    # Related entities (optional - either batch or item)
    batch_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    item_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Alert content
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # Status
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    is_dismissed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<Alert {self.alert_type.value}: {self.title}>"
    
    @property
    def severity_color(self) -> str:
        """Get color code for severity"""
        return {
            AlertSeverity.INFO: "blue",
            AlertSeverity.WARNING: "yellow",
            AlertSeverity.CRITICAL: "red",
        }.get(self.severity, "gray")


