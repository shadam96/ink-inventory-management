"""Item schemas for inventory management"""
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import Field, model_validator

from app.models.item import ItemColor
from app.schemas.common import BaseSchema, TimestampSchema

Currency = Literal["ILS", "USD", "EUR"]


class ItemBase(BaseSchema):
    """Base item schema"""

    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    supplier: str = Field(..., min_length=1, max_length=200)
    unit_of_measure: str = Field(default="KG", max_length=20)
    color: ItemColor = Field(default=ItemColor.OTHER)


class ItemCreate(ItemBase):
    """Schema for creating an item"""

    barcode: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    cost_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: Currency = Field(default="ILS")
    reorder_point: int = Field(default=10, ge=0)
    min_stock: int = Field(default=5, ge=0)
    max_stock: int = Field(default=100, ge=0)

    @model_validator(mode="after")
    def validate_stock_levels(self) -> "ItemCreate":
        if self.min_stock > self.max_stock:
            raise ValueError("מלאי מינימלי לא יכול להיות גדול ממלאי מקסימלי")  # min_stock cannot exceed max_stock
        if self.reorder_point > self.max_stock:
            raise ValueError("נקודת הזמנה לא יכולה להיות גדולה ממלאי מקסימלי")  # reorder_point cannot exceed max_stock
        return self


class ItemUpdate(BaseSchema):
    """Schema for updating an item"""

    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    barcode: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    supplier: Optional[str] = Field(None, min_length=1, max_length=200)
    unit_of_measure: Optional[str] = Field(None, max_length=20)
    color: Optional[ItemColor] = None
    cost_price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[Currency] = None
    reorder_point: Optional[int] = Field(None, ge=0)
    min_stock: Optional[int] = Field(None, ge=0)
    max_stock: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_stock_levels(self) -> "ItemUpdate":
        # Partial update - only validate relationships between fields that
        # are both actually present in this payload. A single-field update
        # (e.g. just raising max_stock) can't be checked against a
        # min_stock/reorder_point that live only in the DB from here.
        if (
            self.min_stock is not None
            and self.max_stock is not None
            and self.min_stock > self.max_stock
        ):
            raise ValueError("מלאי מינימלי לא יכול להיות גדול ממלאי מקסימלי")  # min_stock cannot exceed max_stock
        if (
            self.reorder_point is not None
            and self.max_stock is not None
            and self.reorder_point > self.max_stock
        ):
            raise ValueError("נקודת הזמנה לא יכולה להיות גדולה ממלאי מקסימלי")  # reorder_point cannot exceed max_stock
        return self


class ItemResponse(ItemBase, TimestampSchema):
    """Schema for item response"""

    id: UUID
    barcode: Optional[str]
    description: Optional[str]
    cost_price: Decimal
    currency: Currency
    reorder_point: int
    min_stock: int
    max_stock: int
    
    # Computed fields (populated by service)
    total_quantity_available: Optional[Decimal] = None
    total_inventory_value: Optional[Decimal] = None
    active_batches_count: Optional[int] = None
    is_below_reorder_point: Optional[bool] = None


