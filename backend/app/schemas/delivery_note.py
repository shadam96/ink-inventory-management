"""Delivery note schemas"""
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.models.delivery_note import DeliveryNoteStatus
from app.schemas.common import BaseSchema, TimestampSchema


class DeliveryNoteItemCreate(BaseSchema):
    """Schema for delivery note line item"""
    
    item_id: UUID
    batch_id: UUID
    quantity: Decimal = Field(..., gt=0)


class DeliveryNoteItemResponse(TimestampSchema):
    """Schema for delivery note item response"""
    
    id: UUID
    item_id: UUID
    batch_id: UUID
    quantity: Decimal
    
    # Related data
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    batch_number: Optional[str] = None
    expiration_date: Optional[date] = None


class DeliveryNoteCreate(BaseSchema):
    """Schema for creating a delivery note"""
    
    customer_id: UUID
    items: List[DeliveryNoteItemCreate] = Field(..., min_length=1)
    is_consignment: bool = False
    notes: Optional[str] = None
    issue_date: Optional[date] = None
    delivery_date: Optional[date] = None


class DeliveryNoteUpdate(BaseSchema):
    """Schema for updating a delivery note"""
    
    status: Optional[DeliveryNoteStatus] = None
    is_consignment: Optional[bool] = None
    notes: Optional[str] = None
    issue_date: Optional[date] = None
    delivery_date: Optional[date] = None


class DeliveryNoteResponse(TimestampSchema):
    """Schema for delivery note response"""
    
    id: UUID
    delivery_note_number: str
    customer_id: UUID
    created_by: UUID
    status: DeliveryNoteStatus
    issue_date: Optional[date]
    delivery_date: Optional[date]
    is_consignment: bool
    notes: Optional[str]
    
    # Related data
    customer_name: Optional[str] = None
    created_by_name: Optional[str] = None
    items: List[DeliveryNoteItemResponse] = []
    
    # Computed
    total_quantity: Optional[Decimal] = None
    items_count: Optional[int] = None


