"""Item schemas for inventory management"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class ItemBase(BaseSchema):
    """Base item schema"""
    
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    supplier: str = Field(..., min_length=1, max_length=200)
    unit_of_measure: str = Field(default="KG", max_length=20)


class ItemCreate(ItemBase):
    """Schema for creating an item"""
    
    description: Optional[str] = None
    cost_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    reorder_point: int = Field(default=10, ge=0)
    min_stock: int = Field(default=5, ge=0)
    max_stock: int = Field(default=100, ge=0)


class ItemUpdate(BaseSchema):
    """Schema for updating an item"""
    
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    supplier: Optional[str] = Field(None, min_length=1, max_length=200)
    unit_of_measure: Optional[str] = Field(None, max_length=20)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    reorder_point: Optional[int] = Field(None, ge=0)
    min_stock: Optional[int] = Field(None, ge=0)
    max_stock: Optional[int] = Field(None, ge=0)


class ItemResponse(ItemBase, TimestampSchema):
    """Schema for item response"""
    
    id: UUID
    description: Optional[str]
    cost_price: Decimal
    reorder_point: int
    min_stock: int
    max_stock: int
    
    # Computed fields (populated by service)
    total_quantity_available: Optional[Decimal] = None
    total_inventory_value: Optional[Decimal] = None
    active_batches_count: Optional[int] = None
    is_below_reorder_point: Optional[bool] = None


