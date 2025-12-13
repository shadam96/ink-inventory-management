"""Main FastAPI application entry point"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.redis import redis_client
from app.tasks.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifecycle management"""
    # Startup
    print("🚀 Starting Ink Inventory Management System...")
    await init_db()
    await redis_client.connect()
    print("✅ Database and Redis connected")
    
    # Start scheduler for background tasks
    if not settings.is_development or settings.environment != "test":
        start_scheduler()
        print("✅ Scheduler started")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    shutdown_scheduler()
    await close_db()
    await redis_client.disconnect()
    print("✅ Connections closed")


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
    allow_origins=settings.cors_origins,
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
        "redis": "connected",
        "environment": settings.environment,
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "שגיאה פנימית בשרת",  # Internal server error
            "error": str(exc) if settings.is_development else None,
        },
    )


