"""Customer schemas"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema, TimestampSchema


class CustomerMachineBase(BaseSchema):
    """Base schema for a customer machine"""

    machine_type: str = Field(..., min_length=1, max_length=200)
    installation_date: Optional[date] = None
    notes: Optional[str] = None


class CustomerMachineCreate(CustomerMachineBase):
    """Schema for creating a customer machine"""


class CustomerMachineResponse(CustomerMachineBase, TimestampSchema):
    """Schema for returning a customer machine"""

    id: UUID
    customer_id: UUID


class CustomerBase(BaseSchema):
    """Base customer schema"""

    name: str = Field(..., min_length=1, max_length=200)


class CustomerCreate(CustomerBase):
    """Schema for creating a customer"""

    email: Optional[EmailStr] = None
    phone_primary: Optional[str] = Field(None, max_length=50)
    phone_secondary: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    is_vmi_customer: bool = False
    notes: Optional[str] = None
    machines: List[CustomerMachineCreate] = Field(default_factory=list)


class CustomerUpdate(BaseSchema):
    """Schema for updating a customer"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone_primary: Optional[str] = Field(None, max_length=50)
    phone_secondary: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    is_vmi_customer: Optional[bool] = None
    notes: Optional[str] = None
    machines: Optional[List[CustomerMachineCreate]] = None


class CustomerResponse(CustomerBase, TimestampSchema):
    """Schema for customer response"""

    id: UUID
    email: Optional[str]
    phone_primary: Optional[str]
    phone_secondary: Optional[str]
    address: Optional[str]
    contact_person: Optional[str]
    is_active: bool
    is_vmi_customer: bool
    notes: Optional[str]
    machines: List[CustomerMachineResponse] = Field(default_factory=list)
