"""Shared helper for computing an item's currently available stock.

dashboard_service.py (three call sites) and alert_service.py each
independently reimplemented "sum quantity_available across this item's
ACTIVE, not-yet-expired batches."
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from app.models.batch import Batch, BatchStatus
from app.models.item import Item


def is_active_and_unexpired(batch: Batch, today: date) -> bool:
    """A batch counts toward "available stock" if it's ACTIVE and its
    expiration date hasn't passed yet (as of `today`)."""
    return batch.status == BatchStatus.ACTIVE and batch.expiration_date >= today


def available_quantity(item: Item, today: Optional[date] = None) -> Decimal:
    """Sum of quantity_available across `item`'s ACTIVE batches that
    haven't expired yet (as of `today`, defaulting to date.today()).

    Requires `item.batches` to already be loaded (e.g. via
    `selectinload(Item.batches)`) - this does not issue a query itself.
    """
    today = today or date.today()
    return sum(
        (b.quantity_available for b in item.batches if is_active_and_unexpired(b, today)),
        Decimal("0"),
    )
