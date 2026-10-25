"""Delete all stock data so input testing can start from an empty warehouse.

Deletes batches and everything recorded against them: movements, delivery
notes (with their line items) and alerts, plus customers and their
machines. Keeps the ink types (items) and the rest of the setup: users,
locations and system settings. Customer-role users stay but are unlinked
from their deleted customer, so they see no stock until linked again.

Runs against the database in DATABASE_URL (or backend/.env), printing its
host and row counts and asking for confirmation before deleting anything.

Usage: python reset_inventory_data.py [--yes]
"""
import asyncio
import sys

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker, engine
from app.models import (
    Alert,
    Batch,
    Customer,
    CustomerMachine,
    DeliveryNote,
    DeliveryNoteItem,
    Item,
    Movement,
    User,
)

# Deleted in this order so no row is removed while another still references it.
TABLES_TO_CLEAR = [
    Alert,
    DeliveryNoteItem,
    DeliveryNote,
    Movement,
    Batch,
    CustomerMachine,
    Customer,
]


async def count_rows(session: AsyncSession) -> dict[str, int]:
    """Row counts for the tables that will be cleared, plus items (kept)."""
    counts = {}
    for model in [*TABLES_TO_CLEAR, Item]:
        counts[model.__tablename__] = await session.scalar(select(func.count()).select_from(model))
    return counts


async def count_customer_logins(session: AsyncSession) -> int:
    """Users linked to a customer - kept, but unlinked by the reset."""
    return await session.scalar(
        select(func.count()).select_from(User).where(User.customer_id.is_not(None))
    )


async def reset_inventory_data(session: AsyncSession) -> None:
    """Unlink customer users, then delete every row in TABLES_TO_CLEAR, in
    one transaction."""
    await session.execute(
        update(User).where(User.customer_id.is_not(None)).values(customer_id=None)
    )
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
            print(f">> Customer logins kept but unlinked: {await count_customer_logins(session)}")

            if "--yes" not in sys.argv:
                answer = input('Type "DELETE" to delete these rows: ')
                if answer.strip() != "DELETE":
                    print(">> Aborted, nothing was deleted.")
                    return

            await reset_inventory_data(session)
            print(">> Stock data and customers deleted.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
