"""Schemas for the shared pending-receipt queue"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class PendingReceiptItemCreate(BaseSchema):
    """Payload for adding a row to the shared pending queue."""

    item_id: UUID
    quantity: Decimal = Field(..., gt=0)
    expiration_date: date
    manufacturing_date: Optional[date] = None
    batch_number: Optional[str] = Field(None, max_length=50)
    supplier_batch_number: Optional[str] = Field(None, max_length=100)
    location_id: Optional[UUID] = None
    notes: Optional[str] = None


class PendingReceiptItemResponse(BaseSchema):
    """A single row in the shared pending queue, with display metadata."""

    id: UUID
    item_id: UUID
    quantity: Decimal
    expiration_date: date
    manufacturing_date: Optional[date] = None
    batch_number: Optional[str] = None
    supplier_batch_number: Optional[str] = None
    location_id: Optional[UUID] = None
    notes: Optional[str] = None
    added_by_user_id: UUID
    added_by_username: str
    added_by_full_name: Optional[str] = None
    created_at: datetime

    # Denormalised item info for display
    item_sku: str
    item_name: str
