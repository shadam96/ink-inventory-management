"""User schemas for authentication and management"""
from typing import List, Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

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
    customer_id: Optional[UUID] = None


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
    notification_email: Optional[str] = None
    email_notifications_enabled: bool = False
    customer_id: Optional[UUID] = None
    # Populated by the endpoint from user.locations (relationship, not a
    # plain column) - model_validate doesn't fill this automatically.
    location_ids: List[UUID] = []


class UserLocationAssignment(BaseSchema):
    """Schema for replacing a user's full location assignment set"""

    location_ids: List[UUID]


class NotificationSettingsUpdate(BaseSchema):
    """Schema for updating notification preferences.

    notification_emails accepts a list of email addresses.
    Stored as comma-separated string in the DB.
    Legacy field notification_email is still accepted for backwards compat.
    """

    notification_emails: Optional[List[EmailStr]] = None
    notification_email: Optional[EmailStr] = None
    email_notifications_enabled: bool

    @field_validator("notification_emails", mode="before")
    @classmethod
    def filter_empty(cls, v: object) -> object:
        if isinstance(v, list):
            return [e for e in v if e and str(e).strip()] or None
        return v


class NotificationSettingsResponse(BaseSchema):
    """Schema for notification settings response"""

    email: EmailStr
    notification_email: Optional[str] = None
    notification_emails: List[str] = []
    email_notifications_enabled: bool = False


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


