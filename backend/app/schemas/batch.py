"""Batch schemas for FEFO tracking"""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.models.batch import BatchStatus
from app.schemas.common import BaseSchema, TimestampSchema


class BatchBase(BaseSchema):
    """Base batch schema"""
    
    item_id: UUID
    expiration_date: date
    quantity_received: Decimal = Field(..., gt=0)


class BatchCreate(BatchBase):
    """Schema for creating a batch (goods receipt)"""
    
    batch_number: Optional[str] = Field(None, max_length=50)
    supplier_batch_number: Optional[str] = Field(None, max_length=100)
    location_id: Optional[UUID] = None
    receipt_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None
    
    @field_validator("expiration_date")
    @classmethod
    def expiration_must_be_future(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("תאריך תפוגה חייב להיות בעתיד")  # Expiration date must be in the future
        return v
    
    @field_validator("receipt_date")
    @classmethod
    def receipt_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("תאריך קבלה לא יכול להיות בעתיד")  # Receipt date cannot be in the future
        return v


class BatchUpdate(BaseSchema):
    """Schema for updating a batch"""
    
    location_id: Optional[UUID] = None
    supplier_batch_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    status: Optional[BatchStatus] = None


class BatchResponse(BatchBase, TimestampSchema):
    """Schema for batch response"""
    
    id: UUID
    batch_number: str
    supplier_batch_number: Optional[str]
    quantity_available: Decimal
    receipt_date: date
    location_id: Optional[UUID]
    status: BatchStatus
    notes: Optional[str]
    version: int
    
    # Computed fields
    days_until_expiration: Optional[int] = None
    is_expired: Optional[bool] = None
    inventory_value: Optional[Decimal] = None
    
    # Related data
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    location_code: Optional[str] = None


class BatchSuggestion(BaseSchema):
    """Schema for FEFO batch suggestion"""
    
    batch_id: UUID
    batch_number: str
    quantity_available: Decimal
    expiration_date: date
    days_until_expiration: int
    location_code: Optional[str]
    suggested_quantity: Decimal
    warning_level: str  # "safe", "warning", "critical"


