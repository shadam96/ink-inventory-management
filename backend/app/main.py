"""Main FastAPI application entry point"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import close_db, init_db, ensure_default_users
from app.tasks.scheduler import start_scheduler, shutdown_scheduler

import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifecycle management"""
    # Startup
    logger.info("Starting Ink Inventory Management System...")
    await init_db()
    await ensure_default_users()
    logger.info("Database connected, default users ensured")

    # Start scheduler for background tasks - skip in development (hot
    # reload would spawn duplicate jobs) and in test (deterministic runs
    # without background threads). Previously used `or`, which is a
    # tautology (always True) since environment can't simultaneously be
    # "development" and "test", so the scheduler always started regardless.
    if not settings.is_development and settings.environment != "test":
        start_scheduler()
        logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down...")
    shutdown_scheduler()
    await close_db()
    logger.info("Connections closed")


app = FastAPI(
    title=settings.app_name,
    description="מערכת ניהול מלאי דיו - Ink Inventory Management System with FEFO tracking",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://ink-inventory-management(-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "message": "ברוכים הבאים למערכת ניהול מלאי דיו",  # Welcome to Ink Inventory Management
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.environment,
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions.

    Never send raw exception text to the client - it previously depended
    on settings.is_development, which defaults to True unless ENVIRONMENT
    is explicitly set, so a misconfigured deployment would leak internal
    error details on every 500. Full details go to the server log instead;
    developers should read logs, not trust client responses, for debugging.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "שגיאה פנימית בשרת",  # Internal server error
            "error": None,
        },
    )


