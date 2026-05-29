"""APScheduler setup for background tasks"""
import logging
from datetime import datetime
from decimal import Decimal

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Frankfurter is a free, open-source ECB rate proxy — no API key, daily updates.
FRANKFURTER_LATEST_URL = "https://api.frankfurter.dev/v1/latest"


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


def _invert_frankfurter_rates(payload: dict) -> tuple[Decimal, Decimal] | None:
    """Convert Frankfurter's ILS-base response into our 'foreign-to-ILS' schema.

    Frankfurter returns rates as 1 ILS = X foreign; we store 1 foreign = X ILS,
    so each value is reciprocated. Returns None when the payload is missing or
    has non-positive values — letting the caller keep stale data instead of
    overwriting with garbage.
    """
    rates = payload.get("rates") or {}
    usd_per_ils = rates.get("USD")
    eur_per_ils = rates.get("EUR")
    if not (isinstance(usd_per_ils, (int, float)) and usd_per_ils > 0
            and isinstance(eur_per_ils, (int, float)) and eur_per_ils > 0):
        return None
    return Decimal(str(1 / usd_per_ils)), Decimal(str(1 / eur_per_ils))


async def refresh_fx_rates():
    """Pull the latest ILS-based rates from Frankfurter and persist them.

    On any failure (network, parse, bad data) the existing values are left
    intact; a stale rate is preferable to a zeroed-out one.
    """
    from app.models.system_settings import SystemSettings

    logger.info("Refreshing FX rates from Frankfurter...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                FRANKFURTER_LATEST_URL,
                params={"base": "ILS", "symbols": "USD,EUR"},
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:  # network, timeout, HTTP error, JSON parse — all the same outcome
        logger.warning(f"FX rates refresh failed; keeping existing values: {e}")
        return

    inverted = _invert_frankfurter_rates(data)
    if inverted is None:
        logger.warning(f"FX rates refresh got unexpected payload, keeping existing values: {data}")
        return
    usd_to_ils, eur_to_ils = inverted

    async with async_session_maker() as db:
        try:
            result = await db.execute(select(SystemSettings).where(SystemSettings.id == 1))
            row = result.scalar_one_or_none()
            if row is None:
                row = SystemSettings(id=1, usd_to_ils=usd_to_ils, eur_to_ils=eur_to_ils)
                db.add(row)
            else:
                row.usd_to_ils = usd_to_ils
                row.eur_to_ils = eur_to_ils
            await db.commit()
            logger.info(
                f"FX rates refreshed: 1 USD = {usd_to_ils:.4f} ILS, "
                f"1 EUR = {eur_to_ils:.4f} ILS (Frankfurter date: {data.get('date')})"
            )
        except Exception as e:
            logger.error(f"FX rates DB write failed: {e}")
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

    # Refresh FX rates daily at 6:30 AM (Frankfurter publishes ECB data ~16:00 CET previous day,
    # so a morning Europe-time fetch is always fresh).
    scheduler.add_job(
        refresh_fx_rates,
        CronTrigger(hour=6, minute=30),
        id="fx_rates_refresh",
        name="Daily FX rates refresh from Frankfurter",
        replace_existing=True,
    )

    # Also run both at startup so a fresh deploy gets data immediately.
    scheduler.add_job(
        run_expiration_checks,
        "date",
        run_date=datetime.now(),
        id="startup_expiration_check",
        name="Startup expiration check",
    )
    scheduler.add_job(
        refresh_fx_rates,
        "date",
        run_date=datetime.now(),
        id="startup_fx_rates_refresh",
        name="Startup FX rates refresh",
    )

    logger.info("Scheduler configured with expiration check and FX refresh jobs")


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

