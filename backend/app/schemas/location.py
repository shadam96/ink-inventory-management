"""Location schemas for warehouse management"""
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class LocationBase(BaseSchema):
    """Base location schema"""
    
    warehouse: str = Field(..., min_length=1, max_length=50)
    shelf: str = Field(..., min_length=1, max_length=20)
    position: str = Field(..., min_length=1, max_length=20)


class LocationCreate(LocationBase):
    """Schema for creating a location"""
    
    location_code: Optional[str] = Field(None, max_length=30)
    description: Optional[str] = None


class LocationUpdate(BaseSchema):
    """Schema for updating a location"""
    
    warehouse: Optional[str] = Field(None, min_length=1, max_length=50)
    shelf: Optional[str] = Field(None, min_length=1, max_length=20)
    position: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class LocationResponse(LocationBase, TimestampSchema):
    """Schema for location response"""
    
    id: UUID
    location_code: str
    description: Optional[str]
    is_active: bool
    
    # Computed fields
    batches_count: Optional[int] = None
    active_batches_count: Optional[int] = None


