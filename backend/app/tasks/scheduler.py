"""APScheduler setup for background tasks"""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def run_expiration_checks():
    """Run all expiration and stock checks"""
    from app.services.alert_service import AlertService
    
    logger.info("Running scheduled expiration checks...")
    
    async with async_session_maker() as db:
        try:
            service = AlertService(db)
            result = await service.run_all_checks()
            
            logger.info(
                f"Expiration check complete: "
                f"{result['expiring_alerts']} expiring, "
                f"{result['expired_batches']} expired, "
                f"{result['low_stock_alerts']} low stock, "
                f"{result['dead_stock_alerts']} dead stock"
            )
        except Exception as e:
            logger.error(f"Error in expiration check: {e}")
            await db.rollback()


def setup_scheduler():
    """Configure scheduled jobs"""
    # Run expiration checks daily at 6:00 AM
    scheduler.add_job(
        run_expiration_checks,
        CronTrigger(hour=6, minute=0),
        id="expiration_check",
        name="Daily expiration check",
        replace_existing=True,
    )
    
    # Also run at startup (after 30 seconds delay)
    scheduler.add_job(
        run_expiration_checks,
        "date",
        run_date=datetime.now(),
        id="startup_expiration_check",
        name="Startup expiration check",
    )
    
    logger.info("Scheduler configured with expiration check jobs")


def start_scheduler():
    """Start the scheduler"""
    if not scheduler.running:
        setup_scheduler()
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown")

