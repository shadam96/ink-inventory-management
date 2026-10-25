"""Delete all stock data so input testing can start from an empty warehouse.

Deletes batches and everything recorded against them: movements, delivery
notes (with their line items) and alerts. Keeps the ink types (items) and
the rest of the setup: users, locations, customers and their machines, and
system settings.

Runs against the database in DATABASE_URL (or backend/.env), printing its
host and row counts and asking for confirmation before deleting anything.

Usage: python reset_inventory_data.py [--yes]
"""
import asyncio
import sys

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker, engine
from app.models import Alert, Batch, DeliveryNote, DeliveryNoteItem, Item, Movement

# Deleted in this order so no row is removed while another still references it.
TABLES_TO_CLEAR = [Alert, DeliveryNoteItem, DeliveryNote, Movement, Batch]


async def count_rows(session: AsyncSession) -> dict[str, int]:
    """Row counts for the tables that will be cleared, plus items (kept)."""
    counts = {}
    for model in [*TABLES_TO_CLEAR, Item]:
        counts[model.__tablename__] = await session.scalar(select(func.count()).select_from(model))
    return counts


async def reset_inventory_data(session: AsyncSession) -> None:
    """Delete every row in TABLES_TO_CLEAR in one transaction."""
    for model in TABLES_TO_CLEAR:
        await session.execute(delete(model))
    await session.commit()


async def main() -> None:
    url = engine.url
    print(f">> Database: {url.host or 'localhost'}/{url.database}")

    try:
        async with async_session_maker() as session:
            counts = await count_rows(session)
            print(">> Rows to delete:")
            for model in TABLES_TO_CLEAR:
                print(f"  {model.__tablename__}: {counts[model.__tablename__]}")
            print(f">> Ink types kept: {counts[Item.__tablename__]}")

            if "--yes" not in sys.argv:
                answer = input('Type "DELETE" to delete these rows: ')
                if answer.strip() != "DELETE":
                    print(">> Aborted, nothing was deleted.")
                    return

            await reset_inventory_data(session)
            print(">> Stock data deleted.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
