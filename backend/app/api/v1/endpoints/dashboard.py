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


@router.get("/inventory-value")
async def get_inventory_value(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> dict:
    """Get total inventory value breakdown"""
    service = DashboardService(db)
    return await service.get_inventory_value(location_ids=scope.location_ids)


@router.get("/inventory-distribution")
async def get_inventory_distribution(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> dict:
    """Get inventory distribution by item (for pie chart)"""
    service = DashboardService(db)
    distribution = await service.get_inventory_distribution(location_ids=scope.location_ids)
    return {"items": distribution}


@router.get("/expiration-risk")
async def get_expiration_risk(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> dict:
    """Get expiration risk map (for gauge/risk visualization)"""
    service = DashboardService(db)
    return await service.get_expiration_risk_map(location_ids=scope.location_ids)


@router.get("/low-stock")
async def get_low_stock_items(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
) -> dict:
    """Get items below reorder point"""
    service = DashboardService(db)
    items = await service.get_low_stock_items(location_ids=scope.location_ids)
    return {
        "items": items,
        "count": len(items),
        "critical_count": sum(1 for i in items if i["is_critical"]),
    }


@router.get("/recent-activity")
async def get_recent_activity(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """Get recent activity summary"""
    service = DashboardService(db)
    return await service.get_recent_activity(days, location_ids=scope.location_ids)


@router.get("/movement-trend")
async def get_movement_trend(
    db: DbSession,
    current_user: StaffUser,
    scope: Scope,
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """Get daily receipts/dispatches/scraps series (for trend chart)"""
    service = DashboardService(db)
    return await service.get_movement_trend(days, location_ids=scope.location_ids)
