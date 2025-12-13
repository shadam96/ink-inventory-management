"""User schemas for authentication and management"""
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.models.user import UserRole
from app.schemas.common import BaseSchema, TimestampSchema


class UserBase(BaseSchema):
    """Base user schema"""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for creating a user"""
    
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseSchema):
    """Schema for updating a user"""
    
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class UserResponse(UserBase, TimestampSchema):
    """Schema for user response"""
    
    id: UUID
    role: UserRole
    is_active: bool


class UserLogin(BaseSchema):
    """Schema for login request"""
    
    username: str
    password: str


class Token(BaseSchema):
    """Schema for token response"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseSchema):
    """Schema for token refresh request"""
    
    refresh_token: str


