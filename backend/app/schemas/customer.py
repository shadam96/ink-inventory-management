"""Customer schemas"""
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema, TimestampSchema


class CustomerBase(BaseSchema):
    """Base customer schema"""
    
    name: str = Field(..., min_length=1, max_length=200)


class CustomerCreate(CustomerBase):
    """Schema for creating a customer"""
    
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    is_vmi_customer: bool = False
    notes: Optional[str] = None


class CustomerUpdate(BaseSchema):
    """Schema for updating a customer"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    is_vmi_customer: Optional[bool] = None
    notes: Optional[str] = None


class CustomerResponse(CustomerBase, TimestampSchema):
    """Schema for customer response"""
    
    id: UUID
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    contact_person: Optional[str]
    is_active: bool
    is_vmi_customer: bool
    notes: Optional[str]


