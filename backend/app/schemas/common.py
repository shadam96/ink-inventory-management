"""Common Pydantic schemas"""
from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""
    
    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """Schema with UUID id field"""
    
    id: UUID


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response"""
    
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    
    @property
    def has_next(self) -> bool:
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        return self.page > 1


class MessageResponse(BaseSchema):
    """Simple message response"""
    
    message: str
    success: bool = True
    details: Optional[dict] = None


