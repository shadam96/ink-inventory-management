"""Settings API endpoints"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ManagerUser, get_current_active_user, get_db
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.schemas.user import NotificationSettingsUpdate, NotificationSettingsResponse
from app.services.email_service import email_service
from app.services.system_settings_service import get_or_create_system_settings
from app.core.config import settings


router = APIRouter()


class SystemSettingsResponse(BaseModel):
    """FX rates anchored to ILS (price of 1 unit of foreign currency in ILS),
    plus admin-configurable business thresholds."""
    usd_to_ils: float
    eur_to_ils: float
    try_to_ils: float
    min_shelf_life_days: int
    updated_at: datetime


class SystemSettingsUpdate(BaseModel):
    """Fields a manager can update. FX rates are excluded - the daily
    scheduler is their only writer (see app.tasks.scheduler)."""
    min_shelf_life_days: int = Field(..., ge=0)


def _serialize(row: SystemSettings) -> SystemSettingsResponse:
    return SystemSettingsResponse(
        usd_to_ils=float(row.usd_to_ils),
        eur_to_ils=float(row.eur_to_ils),
        try_to_ils=float(row.try_to_ils),
        min_shelf_life_days=row.min_shelf_life_days,
        updated_at=row.updated_at,
    )


class TestEmailRequest(BaseModel):
    """Request model for sending test email"""
    email: EmailStr


class EmailSettingsResponse(BaseModel):
    """Email settings response"""
    email_configured: bool
    provider: str
    email_from: str


@router.get("/email", response_model=EmailSettingsResponse)
async def get_email_settings(
    current_user: User = Depends(get_current_active_user)
):
    """Get email configuration settings"""
    return EmailSettingsResponse(
        email_configured=email_service.is_configured,
        provider="resend",
        email_from=settings.email_from,
    )


def _parse_notification_emails(raw: str | None) -> list[str]:
    """Split the comma-separated notification_email column into a list."""
    if not raw:
        return []
    return [e.strip() for e in raw.split(",") if e.strip()]


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's notification preferences"""
    emails = _parse_notification_emails(current_user.notification_email)
    return NotificationSettingsResponse(
        email=current_user.email,
        notification_email=current_user.notification_email,
        notification_emails=emails,
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

    # Prefer the new list field; fall back to legacy single-email field
    if payload.notification_emails:
        current_user.notification_email = ",".join(payload.notification_emails)
    elif payload.notification_email:
        current_user.notification_email = payload.notification_email
    else:
        current_user.notification_email = None

    await db.commit()
    await db.refresh(current_user)

    emails = _parse_notification_emails(current_user.notification_email)
    return NotificationSettingsResponse(
        email=current_user.email,
        notification_email=current_user.notification_email,
        notification_emails=emails,
        email_notifications_enabled=current_user.email_notifications_enabled,
    )


@router.get("/system", response_model=SystemSettingsResponse)
async def get_system_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get system-wide settings (FX rates + business thresholds).

    FX rates are refreshed by a daily scheduler job (see app.tasks.scheduler)
    and have no client-facing write endpoint; min_shelf_life_days is editable
    via PUT below.
    """
    row = await get_or_create_system_settings(db)
    return _serialize(row)


@router.put("/system", response_model=SystemSettingsResponse)
async def update_system_settings(
    payload: SystemSettingsUpdate,
    current_user: ManagerUser,
    db: AsyncSession = Depends(get_db),
):
    """Update admin-configurable business thresholds (manager+ only)."""
    row = await get_or_create_system_settings(db)
    row.min_shelf_life_days = payload.min_shelf_life_days
    await db.commit()
    await db.refresh(row)
    return _serialize(row)


@router.post("/email/test")
async def send_test_email(
    request: TestEmailRequest,
    current_user: ManagerUser,
):
    """
    Send a test email to verify configuration (admin/manager only)
    """
    if not email_service.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Email not configured. Set RESEND_API_KEY in environment variables."
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
