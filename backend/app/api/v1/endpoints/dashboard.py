"""Dashboard endpoints for KPIs and analytics"""
from fastapi import APIRouter, Query

from app.api.deps import DbSession, StaffUser, Scope
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/kpis")
async def get_kpis(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> dict:
    """Get main KPI summary for dashboard"""
    service = DashboardService(db)
    return await service.get_kpi_summary(location_ids=scope.location_ids)


@router.get("/movement-trend")
async def get_movement_trend(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """Get daily receipts/dispatches/consumptions/scraps series (for trend chart)"""
    service = DashboardService(db)
    return await service.get_movement_trend(days, location_ids=scope.location_ids)


@router.get("/expiry-timeline")
async def get_expiry_timeline(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> dict:
    """Get active stock bucketed by time to expiration"""
    service = DashboardService(db)
    return await service.get_expiry_timeline(location_ids=scope.location_ids)


@router.get("/stock-coverage")
async def get_stock_coverage(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> dict:
    """Get days of supply per item, from trailing 90-day usage"""
    service = DashboardService(db)
    return await service.get_stock_coverage(location_ids=scope.location_ids)


@router.get("/attention")
async def get_attention_items(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> dict:
    """Get expired/expiring lots, items below minimum and dead stock"""
    service = DashboardService(db)
    return await service.get_attention_items(location_ids=scope.location_ids)
