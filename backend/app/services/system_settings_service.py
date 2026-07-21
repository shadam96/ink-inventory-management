"""Shared accessor for the SystemSettings singleton row (id=1).

Used by the settings API (to read/update FX rates and thresholds) and by
services that need to read a configured business threshold - e.g.
ReceivingService's minimum-shelf-life check - so the DB row is the single
source of truth for both instead of each maintaining its own copy.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_settings import SystemSettings


async def get_or_create_system_settings(db: AsyncSession) -> SystemSettings:
    """Returns the singleton row, creating it with defaults if the boot-time
    migration seed somehow missed (defensive for fresh test databases)."""
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemSettings(
            id=1,
            usd_to_ils=Decimal("3.7"),
            eur_to_ils=Decimal("4.0"),
            min_shelf_life_days=180,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row
