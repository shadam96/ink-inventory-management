"""Alert schemas"""
from typing import Optional
from uuid import UUID

from app.models.alert import AlertSeverity, AlertType
from app.schemas.common import BaseSchema, TimestampSchema


class AlertResponse(TimestampSchema):
    """Schema for alert response"""
    
    id: UUID
    alert_type: AlertType
    severity: AlertSeverity
    batch_id: Optional[UUID]
    item_id: Optional[UUID]
    title: str
    message: str
    is_read: bool
    is_dismissed: bool
    
    # Related data
    batch_number: Optional[str] = None
    item_sku: Optional[str] = None
    item_name: Optional[str] = None


class AlertUpdate(BaseSchema):
    """Schema for updating an alert"""
    
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class AlertCreate(BaseSchema):
    """Schema for creating an alert (internal use)"""
    
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    batch_id: Optional[UUID] = None
    item_id: Optional[UUID] = None


