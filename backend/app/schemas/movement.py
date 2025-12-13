"""Movement schemas for audit trail"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.models.movement import MovementType
from app.schemas.common import BaseSchema, TimestampSchema


class MovementCreate(BaseSchema):
    """Schema for creating a movement"""
    
    batch_id: UUID
    movement_type: MovementType
    quantity: Decimal = Field(..., gt=0)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class MovementResponse(TimestampSchema):
    """Schema for movement response"""
    
    id: UUID
    batch_id: UUID
    user_id: UUID
    movement_type: MovementType
    quantity: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    reference_number: Optional[str]
    timestamp: datetime
    notes: Optional[str]
    
    # Related data
    batch_number: Optional[str] = None
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    user_name: Optional[str] = None


