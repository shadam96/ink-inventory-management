"""Scheduler service for background tasks"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled background tasks"""
    
    _instance = None
    _scheduler: AsyncIOScheduler = None
    
    @classmethod
    def get_instance(cls) -> "SchedulerService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
    
    def setup_jobs(self):
        """Configure scheduled jobs"""
        # Daily expiration check at 6:00 AM
        self._scheduler.add_job(
            self.run_daily_expiration_check,
            CronTrigger(hour=6, minute=0),
            id="daily_expiration_check",
            name="Daily Expiration Check",
            replace_existing=True,
        )
        
        # Low stock check every 4 hours
        self._scheduler.add_job(
            self.run_low_stock_check,
            CronTrigger(hour="*/4"),
            id="low_stock_check",
            name="Low Stock Check",
            replace_existing=True,
        )
        
        # Dead stock check weekly on Sunday at 2:00 AM
        self._scheduler.add_job(
            self.run_dead_stock_check,
            CronTrigger(day_of_week="sun", hour=2),
            id="dead_stock_check",
            name="Dead Stock Check",
            replace_existing=True,
        )
        
        logger.info("Scheduled jobs configured")
    
    def start(self):
        """Start the scheduler"""
        if not self._scheduler.running:
            self.setup_jobs()
            self._scheduler.start()
            logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown")
    
    @staticmethod
    async def run_daily_expiration_check():
        """Run daily expiration check job"""
        logger.info(f"Running daily expiration check at {datetime.now()}")
        
        async with async_session_maker() as session:
            service = AlertService(session)
            
            try:
                # Check expired batches
                expired = await service.check_expired_batches()
                logger.info(f"Found {len(expired)} expired batches")
                
                # Check expiring batches
                expiring = await service.check_expiring_batches()
                logger.info(f"Created {len(expiring)} expiration warnings")
                
                await session.commit()
                
            except Exception as e:
                logger.error(f"Error in daily expiration check: {e}")
                await session.rollback()
    
    @staticmethod
    async def run_low_stock_check():
        """Run low stock check job"""
        logger.info(f"Running low stock check at {datetime.now()}")
        
        async with async_session_maker() as session:
            service = AlertService(session)
            
            try:
                alerts = await service.check_low_stock()
                logger.info(f"Created {len(alerts)} low stock alerts")
                
                await session.commit()
                
            except Exception as e:
                logger.error(f"Error in low stock check: {e}")
                await session.rollback()
    
    @staticmethod
    async def run_dead_stock_check():
        """Run dead stock check job"""
        logger.info(f"Running dead stock check at {datetime.now()}")
        
        async with async_session_maker() as session:
            service = AlertService(session)
            
            try:
                alerts = await service.check_dead_stock()
                logger.info(f"Created {len(alerts)} dead stock alerts")
                
                await session.commit()
                
            except Exception as e:
                logger.error(f"Error in dead stock check: {e}")
                await session.rollback()


@asynccontextmanager
async def lifespan_scheduler():
    """Context manager for scheduler lifecycle"""
    scheduler = SchedulerService.get_instance()
    scheduler.start()
    try:
        yield scheduler
    finally:
        scheduler.shutdown()

