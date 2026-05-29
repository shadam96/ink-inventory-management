"""Settings API endpoints"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.system_settings import SystemSettings
from app.models.user import User, UserRole
from app.schemas.user import NotificationSettingsUpdate, NotificationSettingsResponse
from app.services.email_service import email_service
from app.core.config import settings


router = APIRouter()


class SystemSettingsResponse(BaseModel):
    """FX rates anchored to ILS (price of 1 unit of foreign currency in ILS)."""
    usd_to_ils: float
    eur_to_ils: float
    updated_at: datetime


class SystemSettingsUpdate(BaseModel):
    usd_to_ils: float = Field(gt=0)
    eur_to_ils: float = Field(gt=0)


def _serialize(row: SystemSettings) -> SystemSettingsResponse:
    return SystemSettingsResponse(
        usd_to_ils=float(row.usd_to_ils),
        eur_to_ils=float(row.eur_to_ils),
        updated_at=row.updated_at,
    )


async def _get_or_create_singleton(db: AsyncSession) -> SystemSettings:
    """Returns the singleton row, creating it with defaults if the boot-time
    migration seed somehow missed (defensive for fresh test databases)."""
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemSettings(id=1, usd_to_ils=Decimal("3.7"), eur_to_ils=Decimal("4.0"))
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


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
    """Get system-wide settings (FX rates)."""
    row = await _get_or_create_singleton(db)
    return _serialize(row)


@router.put("/system", response_model=SystemSettingsResponse)
async def update_system_settings(
    payload: SystemSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update system-wide FX rates (admin/manager only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    row = await _get_or_create_singleton(db)
    row.usd_to_ils = Decimal(str(payload.usd_to_ils))
    row.eur_to_ils = Decimal(str(payload.eur_to_ils))
    await db.commit()
    await db.refresh(row)
    return _serialize(row)


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
