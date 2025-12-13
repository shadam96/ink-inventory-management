"""Alert endpoints"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DbSession, ManagerUser
from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.alert_service import AlertService

router = APIRouter()


class AlertResponse(BaseModel):
    """Alert response model"""
    id: UUID
    alert_type: str
    severity: str
    title: str
    message: str
    batch_id: Optional[UUID]
    item_id: Optional[UUID]
    is_read: bool
    is_dismissed: bool
    created_at: str
    

class AlertSummary(BaseModel):
    """Alert summary for dashboard"""
    total_unread: int
    critical: int
    warning: int
    info: int


@router.get("/summary", response_model=AlertSummary)
async def get_alerts_summary(
    db: DbSession,
    current_user: CurrentUser,
) -> AlertSummary:
    """Get summary of unread alerts by severity"""
    service = AlertService(db)
    
    # Count by severity
    result = await db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.is_read == False, Alert.is_dismissed == False)
        .group_by(Alert.severity)
    )
    counts = {row[0]: row[1] for row in result.all()}
    
    total = await service.get_unread_count()
    
    return AlertSummary(
        total_unread=total,
        critical=counts.get(AlertSeverity.CRITICAL, 0),
        warning=counts.get(AlertSeverity.WARNING, 0),
        info=counts.get(AlertSeverity.INFO, 0),
    )


@router.get("")
async def list_alerts(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    alert_type: Optional[AlertType] = None,
    severity: Optional[AlertSeverity] = None,
    unread_only: bool = False,
) -> dict:
    """List alerts with filters"""
    query = (
        select(Alert)
        .order_by(Alert.created_at.desc())
    )
    
    if alert_type:
        query = query.where(Alert.alert_type == alert_type)
    
    if severity:
        query = query.where(Alert.severity == severity)
    
    if unread_only:
        query = query.where(Alert.is_read == False, Alert.is_dismissed == False)
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    items = [
        {
            "id": str(a.id),
            "alert_type": a.alert_type.value,
            "severity": a.severity.value,
            "title": a.title,
            "message": a.message,
            "batch_id": str(a.batch_id) if a.batch_id else None,
            "item_id": str(a.item_id) if a.item_id else None,
            "is_read": a.is_read,
            "is_dismissed": a.is_dismissed,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]
    
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.put("/{alert_id}/read")
async def mark_alert_read(
    alert_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Mark an alert as read"""
    service = AlertService(db)
    await service.mark_as_read(alert_id)
    await db.commit()
    
    return {"success": True, "alert_id": str(alert_id)}


@router.put("/read-all")
async def mark_all_read(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Mark all alerts as read"""
    service = AlertService(db)
    count = await service.mark_all_as_read()
    await db.commit()
    
    return {"success": True, "marked_count": count}


@router.put("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Dismiss an alert"""
    service = AlertService(db)
    await service.dismiss_alert(alert_id)
    await db.commit()
    
    return {"success": True, "alert_id": str(alert_id)}


@router.post("/run-checks")
async def run_alert_checks(
    db: DbSession,
    current_user: ManagerUser,
) -> dict:
    """Manually trigger all alert checks"""
    service = AlertService(db)
    result = await service.run_all_checks()
    
    return {
        "success": True,
        "results": result,
    }
