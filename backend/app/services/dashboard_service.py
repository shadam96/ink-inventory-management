"""Dashboard service for KPIs and analytics"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.movement import Movement, MovementType
from app.models.alert import Alert
from app.models.system_settings import SystemSettings
from app.services.expiration_classifier import (
    CAUTION_THRESHOLD_DAYS,
    CRITICAL_THRESHOLD_DAYS,
    WARNING_THRESHOLD_DAYS,
)
from app.services.stock_helpers import available_quantity


# Movement types that represent stock actually used by customers - the
# demand side of days-of-supply and the cost-of-goods side of turnover.
# Scrap is a loss, not demand, and is reported separately as write-off.
OUTBOUND_USAGE_TYPES = (MovementType.DISPATCH, MovementType.CONSUMPTION)

# Trailing window for usage, write-off and turnover.
HISTORY_WINDOW_DAYS = 90

# Days-ago points whose inventory values are averaged into the "average
# inventory" denominator of turnover and write-off rate (roughly the
# month-end balances over the trailing window).
AVERAGE_INVENTORY_OFFSETS = (0, 30, 60, 90)

LONG_HORIZON_DAYS = 180

# Fixed display order of the expiry timeline.
EXPIRY_BUCKET_KEYS = ("expired", "d0_30", "d31_60", "d61_90", "d91_180", "d181_plus")


def _expiry_bucket(days_until_expiration: int) -> str:
    """Timeline bucket for a batch. Unlike classify_expiration, a batch
    expiring today is still sellable here - matching available_quantity(),
    so the timeline's non-expired buckets add up to the inventory value."""
    if days_until_expiration < 0:
        return "expired"
    if days_until_expiration <= CRITICAL_THRESHOLD_DAYS:
        return "d0_30"
    if days_until_expiration <= WARNING_THRESHOLD_DAYS:
        return "d31_60"
    if days_until_expiration <= CAUTION_THRESHOLD_DAYS:
        return "d61_90"
    if days_until_expiration <= LONG_HORIZON_DAYS:
        return "d91_180"
    return "d181_plus"


def _add(totals: Dict[str, Decimal], key: str, amount: Decimal) -> None:
    totals[key] = totals.get(key, Decimal("0")) + amount


def _floats(totals: Dict[str, Decimal]) -> Dict[str, float]:
    return {key: float(amount) for key, amount in totals.items()}


def _as_date(day: Any) -> date:
    """func.date() comes back as a str on SQLite (tests) but as a date
    object on Postgres (asyncpg, used in prod) - normalize both."""
    return date.fromisoformat(day) if isinstance(day, str) else day


def _scrapped_on(batch: Batch) -> Optional[date]:
    """Scrapping (manually or by the expiry job) only flips the status and
    keeps quantity_available, with no Movement - scrapped_at records when.
    A scrapped batch without it is treated as scrapped long ago."""
    if batch.status != BatchStatus.SCRAP:
        return None
    return batch.scrapped_at.date() if batch.scrapped_at else date.min


def _items_batches_loader(location_ids: Optional[List[UUID]]):
    """selectinload(Item.batches), optionally filtered to only load batches
    at the given locations - so available_quantity() downstream operates
    on an already-scoped collection with no other changes needed."""
    if location_ids is None:
        return selectinload(Item.batches)
    return selectinload(Item.batches.and_(Batch.location_id.in_(location_ids)))


class DashboardService:
    """Service for dashboard KPIs and analytics"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_movement_trend(
        self, days: int = 7, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Get daily receipts/dispatches/consumptions/scraps for the last
        `days` days (today included), zero-filled so a trend chart has no
        gaps on days without movements.

        Quantities mix units of measure across items, so each day also
        carries the cost value of receipts and of outbound usage (dispatch +
        consumption), bucketed by item currency for client-side conversion.

        location_ids restricts to movements whose batch is at one of those
        locations - None means unrestricted.
        """
        today = date.today()
        start_date = today - timedelta(days=days - 1)

        query = (
            select(
                func.date(Movement.timestamp).label("day"),
                Movement.movement_type,
                Item.currency,
                func.sum(Movement.quantity).label("total"),
                func.sum(Movement.quantity * Item.cost_price).label("value"),
            )
            .join(Batch, Movement.batch_id == Batch.id)
            .join(Item, Batch.item_id == Item.id)
            .where(func.date(Movement.timestamp) >= start_date)
        )
        if location_ids is not None:
            query = query.where(Batch.location_id.in_(location_ids))
        query = query.group_by(func.date(Movement.timestamp), Movement.movement_type, Item.currency)

        result = await self.db.execute(query)

        totals: Dict[date, Dict[MovementType, Decimal]] = {}
        values: Dict[date, Dict[str, Dict[str, Decimal]]] = {}
        for day, movement_type, currency, total, value in result.all():
            day = _as_date(day)
            day_totals = totals.setdefault(day, {})
            day_totals[movement_type] = day_totals.get(movement_type, Decimal("0")) + Decimal(str(total))
            if movement_type == MovementType.RECEIPT:
                flow = "receipts"
            elif movement_type in OUTBOUND_USAGE_TYPES:
                flow = "outbound"
            else:
                continue
            _add(values.setdefault(day, {}).setdefault(flow, {}), currency or "ILS", Decimal(str(value)))

        num_days = (today - start_date).days + 1
        series = []
        for offset in range(num_days):
            day = start_date + timedelta(days=offset)
            day_totals = totals.get(day, {})
            day_values = values.get(day, {})
            series.append({
                "date": day.isoformat(),
                "receipts": float(day_totals.get(MovementType.RECEIPT, 0)),
                "dispatches": float(day_totals.get(MovementType.DISPATCH, 0)),
                "consumptions": float(day_totals.get(MovementType.CONSUMPTION, 0)),
                "scraps": float(day_totals.get(MovementType.SCRAP, 0)),
                "receipts_value_by_currency": _floats(day_values.get("receipts", {})),
                "outbound_value_by_currency": _floats(day_values.get("outbound", {})),
            })

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "series": series,
        }

    async def get_expiry_timeline(
        self, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Active stock bucketed by how soon it expires (see _expiry_bucket),
        each bucket's value kept per item currency for client-side FX
        conversion and its quantity kept per unit of measure (liters and
        kilograms can't be summed together)."""
        today = date.today()
        query = (
            select(Batch)
            .options(selectinload(Batch.item))
            .where(Batch.status == BatchStatus.ACTIVE, Batch.quantity_available > 0)
        )
        if location_ids is not None:
            query = query.where(Batch.location_id.in_(location_ids))
        batches = (await self.db.execute(query)).scalars().all()

        buckets: Dict[str, Dict[str, Any]] = {
            key: {"value_by_currency": {}, "quantity_by_unit": {}, "batches": 0}
            for key in EXPIRY_BUCKET_KEYS
        }
        for batch in batches:
            item = batch.item
            bucket = buckets[_expiry_bucket((batch.expiration_date - today).days)]
            _add(bucket["value_by_currency"], item.currency or "ILS", batch.quantity_available * item.cost_price)
            _add(bucket["quantity_by_unit"], item.unit_of_measure, batch.quantity_available)
            bucket["batches"] += 1

        return {
            "buckets": [
                {
                    "key": key,
                    "value_by_currency": _floats(buckets[key]["value_by_currency"]),
                    "quantity_by_unit": _floats(buckets[key]["quantity_by_unit"]),
                    "batches": buckets[key]["batches"],
                }
                for key in EXPIRY_BUCKET_KEYS
            ]
        }

    async def get_stock_coverage(
        self,
        location_ids: Optional[List[UUID]] = None,
        window_days: int = HISTORY_WINDOW_DAYS,
    ) -> Dict[str, Any]:
        """Days of supply per item: usable stock on hand divided by average
        daily usage (dispatch + consumption) over the trailing window.

        Items with less history than the window average over the days since
        their first receipt instead, so a new item isn't diluted by days it
        didn't exist. days_of_supply is 0 when out of stock and None when
        there is stock but no usage at all. Sorted most urgent first,
        no-usage items last.
        """
        today = date.today()
        window_start = today - timedelta(days=window_days)

        items = (
            await self.db.execute(select(Item).options(_items_batches_loader(location_ids)))
        ).scalars().all()

        usage_query = (
            select(Batch.item_id, func.sum(Movement.quantity))
            .join(Batch, Movement.batch_id == Batch.id)
            .where(
                Movement.movement_type.in_(OUTBOUND_USAGE_TYPES),
                func.date(Movement.timestamp) > window_start,
            )
            .group_by(Batch.item_id)
        )
        if location_ids is not None:
            usage_query = usage_query.where(Batch.location_id.in_(location_ids))
        usage = {
            item_id: Decimal(str(total))
            for item_id, total in (await self.db.execute(usage_query)).all()
        }

        rows = []
        for item in items:
            quantity = available_quantity(item, today)
            used = usage.get(item.id, Decimal("0"))
            if quantity == 0 and used == 0 and item.reorder_point <= 0:
                continue

            first_receipt = min((b.receipt_date for b in item.batches), default=today)
            # Usage covers the window's days up to and including today, so
            # the receipt day itself counts as a day of history.
            history_days = min(window_days, (today - first_receipt).days + 1)
            avg_daily_usage = used / history_days
            if quantity == 0:
                days_of_supply = 0.0
            elif avg_daily_usage > 0:
                days_of_supply = float(quantity / avg_daily_usage)
            else:
                days_of_supply = None

            if quantity == 0:
                status = "out"
            elif quantity < item.min_stock:
                status = "below_min"
            elif quantity < item.reorder_point:
                status = "below_reorder"
            else:
                status = "ok"

            rows.append({
                "item_id": str(item.id),
                "sku": item.sku,
                "name": item.name,
                "color": item.color.value,
                "unit": item.unit_of_measure,
                "quantity": float(quantity),
                "reorder_point": item.reorder_point,
                "min_stock": item.min_stock,
                "avg_daily_usage": float(avg_daily_usage),
                "days_of_supply": days_of_supply,
                "status": status,
            })

        rows.sort(key=lambda r: (r["days_of_supply"] is None, r["days_of_supply"] or 0, r["sku"]))
        return {"window_days": window_days, "items": rows}

    async def get_attention_items(
        self, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Exceptions someone should act on today:

        - expired_on_shelf: active lots past their expiration date (the
          nightly expiry job normally scraps these, so anything here is
          still waiting on it or on someone)
        - expiring_soon: lots expiring within the critical window, soonest first
        - below_min: items whose usable stock is under min_stock
        - dead_stock: items with stock whose last movement is more than
          settings.dead_stock_days ago - same rule as
          AlertService.check_dead_stock
        """
        today = date.today()

        lots_query = (
            select(Batch)
            .options(selectinload(Batch.item), selectinload(Batch.location))
            .where(
                Batch.status == BatchStatus.ACTIVE,
                Batch.quantity_available > 0,
                Batch.expiration_date <= today + timedelta(days=CRITICAL_THRESHOLD_DAYS),
            )
            .order_by(Batch.expiration_date)
        )
        if location_ids is not None:
            lots_query = lots_query.where(Batch.location_id.in_(location_ids))
        lots = (await self.db.execute(lots_query)).scalars().all()

        def lot_row(batch: Batch) -> Dict[str, Any]:
            item = batch.item
            return {
                "batch_id": str(batch.id),
                "batch_number": batch.batch_number,
                "item_id": str(item.id),
                "sku": item.sku,
                "name": item.name,
                "unit": item.unit_of_measure,
                "quantity": float(batch.quantity_available),
                "value": float(batch.quantity_available * item.cost_price),
                "currency": item.currency or "ILS",
                "expiration_date": batch.expiration_date.isoformat(),
                "days_until_expiration": (batch.expiration_date - today).days,
                "location_code": batch.location.location_code if batch.location else None,
            }

        items = (
            await self.db.execute(select(Item).options(_items_batches_loader(location_ids)))
        ).scalars().all()

        last_movement_query = (
            select(Batch.item_id, func.max(Movement.timestamp))
            .join(Batch, Movement.batch_id == Batch.id)
            .where(Batch.status == BatchStatus.ACTIVE)
            .group_by(Batch.item_id)
        )
        if location_ids is not None:
            last_movement_query = last_movement_query.where(Batch.location_id.in_(location_ids))
        # max(timestamp) is an ISO string on SQLite, a datetime on Postgres.
        last_movement = {
            item_id: (date.fromisoformat(ts[:10]) if isinstance(ts, str) else ts.date())
            for item_id, ts in (await self.db.execute(last_movement_query)).all()
        }

        below_min = []
        dead_stock = []
        for item in items:
            quantity = available_quantity(item, today)
            if quantity < item.min_stock:
                below_min.append({
                    "item_id": str(item.id),
                    "sku": item.sku,
                    "name": item.name,
                    "unit": item.unit_of_measure,
                    "quantity": float(quantity),
                    "min_stock": item.min_stock,
                    "reorder_point": item.reorder_point,
                })

            last_activity = last_movement.get(item.id)
            if quantity > 0 and last_activity is not None:
                days_inactive = (today - last_activity).days
                if days_inactive > settings.dead_stock_days:
                    dead_stock.append({
                        "item_id": str(item.id),
                        "sku": item.sku,
                        "name": item.name,
                        "unit": item.unit_of_measure,
                        "quantity": float(quantity),
                        "value": float(quantity * item.cost_price),
                        "currency": item.currency or "ILS",
                        "last_movement_date": last_activity.isoformat(),
                        "days_inactive": days_inactive,
                    })

        below_min.sort(key=lambda r: (r["quantity"] / r["min_stock"], r["sku"]))
        dead_stock.sort(key=lambda r: -r["days_inactive"])

        return {
            "expired_on_shelf": [lot_row(b) for b in lots if b.expiration_date < today],
            "expiring_soon": [lot_row(b) for b in lots if b.expiration_date >= today],
            "below_min": below_min,
            "dead_stock": dead_stock,
        }

    async def _inventory_value_history(
        self, offsets: tuple[int, ...], location_ids: Optional[List[UUID]] = None
    ) -> Dict[int, Dict[str, Decimal]]:
        """Inventory value (per currency) as it stood at the end of the day
        `offset` days ago, for each offset - rebuilt from today's quantities
        by undoing every movement after that day (quantity_after -
        quantity_before is each movement's signed effect, adjustments
        included). Offset 0 equals get_kpi_summary's inventory_value_by_currency.

        Counts the same stock available_quantity() does: received by then,
        not yet expired then, and - for scrapped batches - not yet scrapped.
        """
        today = date.today()
        since = today - timedelta(days=max(offsets))

        delta_query = (
            select(
                Movement.batch_id,
                func.date(Movement.timestamp),
                func.sum(Movement.quantity_after - Movement.quantity_before),
            )
            .where(func.date(Movement.timestamp) > since)
            .group_by(Movement.batch_id, func.date(Movement.timestamp))
        )
        if location_ids is not None:
            delta_query = delta_query.join(Batch, Movement.batch_id == Batch.id).where(
                Batch.location_id.in_(location_ids)
            )
        deltas: Dict[UUID, List[tuple[date, Decimal]]] = {}
        for batch_id, day, delta in (await self.db.execute(delta_query)).all():
            deltas.setdefault(batch_id, []).append((_as_date(day), Decimal(str(delta))))

        batch_query = (
            select(Batch)
            .options(selectinload(Batch.item))
            .where(or_(Batch.quantity_available > 0, Batch.id.in_(list(deltas))))
        )
        if location_ids is not None:
            batch_query = batch_query.where(Batch.location_id.in_(location_ids))
        batches = (await self.db.execute(batch_query)).scalars().all()

        values: Dict[int, Dict[str, Decimal]] = {offset: {} for offset in offsets}
        for batch in batches:
            scrapped_on = _scrapped_on(batch)
            for offset in offsets:
                day = today - timedelta(days=offset)
                if batch.receipt_date > day or batch.expiration_date < day:
                    continue
                if scrapped_on is not None and scrapped_on <= day:
                    continue
                quantity = batch.quantity_available - sum(
                    (delta for moved_on, delta in deltas.get(batch.id, []) if moved_on > day),
                    Decimal("0"),
                )
                if quantity > 0:
                    _add(values[offset], batch.item.currency or "ILS", quantity * batch.item.cost_price)
        return values

    async def _movement_cost_by_currency(
        self,
        movement_types: tuple[MovementType, ...],
        since: date,
        location_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Decimal]:
        """Cost of the given movements after `since`, per item currency."""
        query = (
            select(Item.currency, Item.cost_price, func.sum(Movement.quantity))
            .select_from(Movement)
            .join(Batch, Movement.batch_id == Batch.id)
            .join(Item, Batch.item_id == Item.id)
            .where(
                Movement.movement_type.in_(movement_types),
                func.date(Movement.timestamp) > since,
            )
            .group_by(Item.id, Item.currency, Item.cost_price)
        )
        if location_ids is not None:
            query = query.where(Batch.location_id.in_(location_ids))
        totals: Dict[str, Decimal] = {}
        for currency, cost_price, quantity in (await self.db.execute(query)).all():
            _add(totals, currency or "ILS", Decimal(str(quantity)) * cost_price)
        return totals

    async def _write_off_by_currency(
        self, since: date, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Decimal]:
        """Value written off after `since`: batches scrapped in that period
        (which keep the scrapped quantity in quantity_available) plus any
        SCRAP movements (partial write-offs)."""
        query = (
            select(Batch)
            .options(selectinload(Batch.item))
            .where(Batch.status == BatchStatus.SCRAP, Batch.quantity_available > 0)
        )
        if location_ids is not None:
            query = query.where(Batch.location_id.in_(location_ids))

        totals = await self._movement_cost_by_currency((MovementType.SCRAP,), since, location_ids)
        for batch in (await self.db.execute(query)).scalars().all():
            if _scrapped_on(batch) > since:
                _add(totals, batch.item.currency or "ILS", batch.quantity_available * batch.item.cost_price)
        return totals

    async def _get_fx_rates(self) -> tuple[Decimal, Decimal, Decimal]:
        """Returns (usd_to_ils, eur_to_ils, try_to_ils) from the SystemSettings
        singleton, falling back to its column defaults if the row is
        somehow missing (defensive for fresh test databases)."""
        result = await self.db.execute(select(SystemSettings).where(SystemSettings.id == 1))
        row = result.scalar_one_or_none()
        if row is None:
            return Decimal("3.7"), Decimal("4.0"), Decimal("0.11")
        return row.usd_to_ils, row.eur_to_ils, row.try_to_ils

    @staticmethod
    def _sum_in_ils(
        amounts_by_currency: Dict[str, Decimal],
        usd_to_ils: Decimal,
        eur_to_ils: Decimal,
        try_to_ils: Decimal,
    ) -> Decimal:
        rates = {"ILS": Decimal("1"), "USD": usd_to_ils, "EUR": eur_to_ils, "TRY": try_to_ils}
        return sum(
            (amount * rates.get(ccy, Decimal("1")) for ccy, amount in amounts_by_currency.items()),
            Decimal("0"),
        )

    async def get_kpi_summary(
        self, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Get all KPIs for dashboard.

        Fetches Items+Batches once and derives inventory value and low-stock
        counts from that single dataset rather than re-running
        `select(Item).options(selectinload(...))` per figure.

        location_ids restricts everything below (batches, movements, unread
        alerts) to those locations - None means unrestricted.
        """
        today = date.today()

        result = await self.db.execute(
            select(Item).options(_items_batches_loader(location_ids))
        )
        items = result.scalars().all()

        inventory_by_currency: Dict[str, Decimal] = {}
        items_with_stock = 0
        low_stock_count = 0
        critical_low_stock_count = 0

        for item in items:
            active_qty = available_quantity(item, today)

            if active_qty > 0:
                items_with_stock += 1
                _add(inventory_by_currency, item.currency or "ILS", active_qty * item.cost_price)

            if active_qty < item.reorder_point:
                low_stock_count += 1
                if active_qty < item.min_stock:
                    critical_low_stock_count += 1

        # Unread alerts count (item-only alerts excluded when scoped, same
        # convention as the alerts endpoint)
        unread_query = select(func.count(Alert.id)).where(
            Alert.is_read == False, Alert.is_dismissed == False
        )
        if location_ids is not None:
            unread_query = unread_query.join(Batch, Alert.batch_id == Batch.id).where(
                Batch.location_id.in_(location_ids)
            )
        result = await self.db.execute(unread_query)
        unread_alerts = result.scalar() or 0

        # Turnover and write-off rate are ratios over the trailing window,
        # against the average of the inventory value sampled across it - so
        # they're computed in ILS. With less history than the window (just
        # after go-live), usage per day and the average only cover the days
        # since the first receipt, rather than being diluted by days before
        # there was any stock.
        usd_to_ils, eur_to_ils, try_to_ils = await self._get_fx_rates()
        window_start = today - timedelta(days=HISTORY_WINDOW_DAYS)
        past_offsets = tuple(offset for offset in AVERAGE_INVENTORY_OFFSETS if offset > 0)
        history = await self._inventory_value_history(past_offsets, location_ids)
        history[0] = inventory_by_currency
        write_off = await self._write_off_by_currency(window_start, location_ids)
        outbound_cost = await self._movement_cost_by_currency(OUTBOUND_USAGE_TYPES, window_start, location_ids)

        first_receipt = min((b.receipt_date for item in items for b in item.batches), default=today)
        days_since_first_receipt = max(0, (today - first_receipt).days)
        history_days = min(HISTORY_WINDOW_DAYS, days_since_first_receipt + 1)
        sampled_offsets = [offset for offset in AVERAGE_INVENTORY_OFFSETS if offset <= days_since_first_receipt]

        def in_ils(amounts: Dict[str, Decimal]) -> Decimal:
            return self._sum_in_ils(amounts, usd_to_ils, eur_to_ils, try_to_ils)

        avg_inventory_ils = sum(
            (in_ils(history[offset]) for offset in sampled_offsets), Decimal("0")
        ) / len(sampled_offsets)
        daily_outbound_ils = in_ils(outbound_cost) / history_days

        return {
            "inventory_value_by_currency": _floats(inventory_by_currency),
            "inventory_value_30d_ago_by_currency": _floats(history[30]),
            "items_in_stock": items_with_stock,
            "low_stock_items": low_stock_count,
            "critical_low_stock": critical_low_stock_count,
            "unread_alerts": unread_alerts,
            "write_off_90d_value_by_currency": _floats(write_off),
            "write_off_90d_rate": (
                round(float(in_ils(write_off) / avg_inventory_ils) * 100, 2) if avg_inventory_ils > 0 else 0
            ),
            "avg_inventory_value_ils": float(avg_inventory_ils),
            "turnover_annualized": (
                float(daily_outbound_ils * 365 / avg_inventory_ils) if avg_inventory_ils > 0 else 0
            ),
            "days_on_hand": float(avg_inventory_ils / daily_outbound_ils) if daily_outbound_ils > 0 else None,
        }
