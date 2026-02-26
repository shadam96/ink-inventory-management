"""Settings API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.user import User, UserRole
from app.schemas.user import NotificationSettingsUpdate, NotificationSettingsResponse
from app.services.email_service import email_service
from app.core.config import settings


router = APIRouter()


class TestEmailRequest(BaseModel):
    """Request model for sending test email"""
    email: EmailStr


class EmailSettingsResponse(BaseModel):
    """Email settings response"""
    email_configured: bool
    smtp_host: str
    smtp_port: int
    email_from: str


@router.get("/email", response_model=EmailSettingsResponse)
async def get_email_settings(
    current_user: User = Depends(get_current_active_user)
):
    """Get email configuration settings"""
    return EmailSettingsResponse(
        email_configured=bool(settings.smtp_user and settings.smtp_password),
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        email_from=settings.email_from
    )


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's notification preferences"""
    return NotificationSettingsResponse(
        email=current_user.email,
        notification_email=current_user.notification_email,
        email_notifications_enabled=current_user.email_notifications_enabled,
    )


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    payload: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's notification preferences"""
    current_user.email_notifications_enabled = payload.email_notifications_enabled
    current_user.notification_email = payload.notification_email
    await db.commit()
    await db.refresh(current_user)
    
    return NotificationSettingsResponse(
        email=current_user.email,
        notification_email=current_user.notification_email,
        email_notifications_enabled=current_user.email_notifications_enabled,
    )


@router.post("/email/test")
async def send_test_email(
    request: TestEmailRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a test email to verify configuration (admin only)
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if not settings.smtp_user or not settings.smtp_password:
        raise HTTPException(
            status_code=400, 
            detail="Email not configured. Please set SMTP_USER and SMTP_PASSWORD in environment variables."
        )
    
    try:
        await email_service.send_test_email(request.email)
        return {
            "success": True,
            "message": f"Test email sent to {request.email}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test email: {str(e)}"
        )
