"""Dashboard endpoints for KPIs and analytics"""
from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/kpis")
async def get_kpis(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Get main KPI summary for dashboard"""
    service = DashboardService(db)
    return await service.get_kpi_summary()


@router.get("/inventory-value")
async def get_inventory_value(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Get total inventory value breakdown"""
    service = DashboardService(db)
    return await service.get_inventory_value()


@router.get("/inventory-distribution")
async def get_inventory_distribution(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Get inventory distribution by item (for pie chart)"""
    service = DashboardService(db)
    distribution = await service.get_inventory_distribution()
    return {"items": distribution}


@router.get("/expiration-risk")
async def get_expiration_risk(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Get expiration risk map (for gauge/risk visualization)"""
    service = DashboardService(db)
    return await service.get_expiration_risk_map()


@router.get("/low-stock")
async def get_low_stock_items(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Get items below reorder point"""
    service = DashboardService(db)
    items = await service.get_low_stock_items()
    return {
        "items": items,
        "count": len(items),
        "critical_count": sum(1 for i in items if i["is_critical"]),
    }


@router.get("/recent-activity")
async def get_recent_activity(
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """Get recent activity summary"""
    service = DashboardService(db)
    return await service.get_recent_activity(days)
