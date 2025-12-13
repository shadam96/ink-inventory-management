"""API v1 router - aggregates all endpoint routers"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    inventory,
    batches,
    locations,
    customers,
    receiving,
    picking,
    movements,
    delivery_notes,
    alerts,
    dashboard,
)

api_router = APIRouter()

# Authentication
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Inventory Management
api_router.include_router(
    inventory.router,
    prefix="/items",
    tags=["Items"]
)

api_router.include_router(
    batches.router,
    prefix="/batches",
    tags=["Batches"]
)

api_router.include_router(
    locations.router,
    prefix="/locations",
    tags=["Locations"]
)

api_router.include_router(
    customers.router,
    prefix="/customers",
    tags=["Customers"]
)

# Goods Receipt
api_router.include_router(
    receiving.router,
    prefix="/receiving",
    tags=["Goods Receipt"]
)

# Picking & Dispatch
api_router.include_router(
    picking.router,
    prefix="/picking",
    tags=["Picking"]
)

# Movement History
api_router.include_router(
    movements.router,
    prefix="/movements",
    tags=["Movements"]
)

# Delivery Notes
api_router.include_router(
    delivery_notes.router,
    prefix="/delivery-notes",
    tags=["Delivery Notes"]
)

# Alerts
api_router.include_router(
    alerts.router,
    prefix="/alerts",
    tags=["Alerts"]
)

# Dashboard
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"]
)


