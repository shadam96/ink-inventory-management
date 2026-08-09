"""Dashboard service for KPIs and analytics"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.movement import Movement, MovementType
from app.models.alert import Alert
from app.models.delivery_note import DeliveryNote, DeliveryNoteStatus
from app.models.system_settings import SystemSettings
from app.services.expiration_classifier import classify_expiration
from app.services.stock_helpers import available_quantity, is_active_and_unexpired


def _items_batches_loader(location_ids: Optional[List[UUID]]):
    """selectinload(Item.batches), optionally filtered to only load batches
    at the given locations - so available_quantity()/is_active_and_unexpired()
    downstream operate on an already-scoped collection with no other
    changes needed."""
    if location_ids is None:
        return selectinload(Item.batches)
    return selectinload(Item.batches.and_(Batch.location_id.in_(location_ids)))


class DashboardService:
    """Service for dashboard KPIs and analytics"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_inventory_value(
        self, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Calculate inventory value bucketed by per-item currency.

        Items declare their own currency on creation. Summing raw cost prices
        across currencies would be nonsense, so the dashboard receives a
        per-currency breakdown and applies FX conversion client-side using the
        rates from SystemSettings.

        location_ids restricts the underlying batches to those locations
        (staff scoping) - None means unrestricted.
        """
        result = await self.db.execute(
            select(Item).options(_items_batches_loader(location_ids))
        )
        items = result.scalars().all()

        today = date.today()
        totals_by_currency: Dict[str, Decimal] = {}
        total_quantity = Decimal("0")
        items_count = 0

        for item in items:
            active_qty = available_quantity(item, today)
            if active_qty > 0:
                items_count += 1
                total_quantity += active_qty
                ccy = item.currency or "ILS"
                totals_by_currency[ccy] = (
                    totals_by_currency.get(ccy, Decimal("0"))
                    + active_qty * item.cost_price
                )

        return {
            "totals_by_currency": {
                ccy: float(amount) for ccy, amount in totals_by_currency.items()
            },
            "total_quantity": float(total_quantity),
            "items_with_stock": items_count,
        }
    
    async def get_inventory_distribution(
        self, location_ids: Optional[List[UUID]] = None
    ) -> List[Dict[str, Any]]:
        """Get inventory distribution by item (for pie chart)"""
        result = await self.db.execute(
            select(Item).options(_items_batches_loader(location_ids))
        )
        items = result.scalars().all()
        
        today = date.today()
        distribution = []
        
        for item in items:
            active_qty = available_quantity(item, today)
            if active_qty > 0:
                value = float(active_qty * item.cost_price)
                distribution.append({
                    "item_id": str(item.id),
                    "sku": item.sku,
                    "name": item.name,
                    "quantity": float(active_qty),
                    "value": value,
                    "unit": item.unit_of_measure,
                    "color": item.color.value,
                })
        
        # Sort by value descending
        distribution.sort(key=lambda x: x["value"], reverse=True)
        return distribution
    
    async def get_expiration_risk_map(
        self, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Get expiration risk breakdown (for gauge/risk map)"""
        today = date.today()

        query = (
            select(Batch)
            .options(selectinload(Batch.item))
            .where(
                Batch.status == BatchStatus.ACTIVE,
                Batch.quantity_available > 0,
            )
        )
        if location_ids is not None:
            query = query.where(Batch.location_id.in_(location_ids))

        result = await self.db.execute(query)
        batches = result.scalars().all()
        
        # value_by_currency mirrors get_inventory_value's pattern: summing
        # raw cost prices across currencies would be nonsense (an item
        # priced in USD and one in ILS aren't the same "value"), so each
        # level's value is bucketed by the item's own currency instead of
        # mixed into one number. The frontend converts to a single display
        # currency using SystemSettings FX rates, same as inventory_value.
        # Bucket boundaries are classify_expiration's: expired (<=0 days),
        # critical (1-30), warning (31-60), caution (61-90), safe (91+).
        risk_levels: Dict[str, Dict[str, Any]] = {
            "expired": {"quantity": Decimal("0"), "value_by_currency": {}, "batches": 0},
            "critical": {"quantity": Decimal("0"), "value_by_currency": {}, "batches": 0},
            "warning": {"quantity": Decimal("0"), "value_by_currency": {}, "batches": 0},
            "caution": {"quantity": Decimal("0"), "value_by_currency": {}, "batches": 0},
            "safe": {"quantity": Decimal("0"), "value_by_currency": {}, "batches": 0},
        }

        for batch in batches:
            days_until = (batch.expiration_date - today).days
            cost = batch.item.cost_price if batch.item else Decimal("0")
            ccy = (batch.item.currency if batch.item else None) or "ILS"
            value = batch.quantity_available * cost

            level = classify_expiration(days_until)

            bucket = risk_levels[level]
            bucket["quantity"] += batch.quantity_available
            bucket["value_by_currency"][ccy] = bucket["value_by_currency"].get(ccy, Decimal("0")) + value
            bucket["batches"] += 1

        # Convert to float for JSON
        currency_totals: Dict[str, float] = {}
        for level in risk_levels:
            risk_levels[level]["quantity"] = float(risk_levels[level]["quantity"])
            risk_levels[level]["value_by_currency"] = {
                ccy: float(amount) for ccy, amount in risk_levels[level]["value_by_currency"].items()
            }
            for ccy, amount in risk_levels[level]["value_by_currency"].items():
                currency_totals[ccy] = currency_totals.get(ccy, 0.0) + amount

        # No per-level "percentage" field: computing one accurately
        # requires converting every currency to a common one first, and
        # only the frontend has the FX rates to do that (via
        # convertToDisplayCurrency, same as inventory_value_by_currency).
        # The frontend derives pie-chart proportions from the converted
        # values directly.

        return {
            "risk_levels": risk_levels,
            "total_value_by_currency": currency_totals,
            "color_codes": {
                "expired": "#000000",   # Black
                "critical": "#DC2626",  # Red
                "warning": "#F59E0B",   # Yellow/Orange
                "caution": "#FBBF24",   # Light Yellow
                "safe": "#10B981",      # Green
            }
        }
    
    async def get_low_stock_items(
        self, location_ids: Optional[List[UUID]] = None
    ) -> List[Dict[str, Any]]:
        """Get items below reorder point.

        reorder_point/min_stock are global, item-level thresholds - when
        location_ids is set, "low stock" means "low at these locations,"
        which is the intended meaning for a location-scoped worker (they
        shouldn't be alarmed by a shortage in a warehouse they don't
        operate). There's no per-location reorder point in the schema, so
        the thresholds themselves stay unscoped.
        """
        result = await self.db.execute(
            select(Item).options(_items_batches_loader(location_ids))
        )
        items = result.scalars().all()
        
        today = date.today()
        low_stock = []
        
        for item in items:
            available = available_quantity(item, today)

            if available < item.reorder_point:
                low_stock.append({
                    "item_id": str(item.id),
                    "sku": item.sku,
                    "name": item.name,
                    "current_quantity": float(available),
                    "reorder_point": item.reorder_point,
                    "min_stock": item.min_stock,
                    "shortage": float(item.reorder_point - available),
                    "is_critical": available < item.min_stock,
                })
        
        # Sort by shortage descending
        low_stock.sort(key=lambda x: x["shortage"], reverse=True)
        return low_stock
    
    async def get_recent_activity(
        self, days: int = 7, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Get recent activity summary.

        location_ids restricts movements/alerts to those tied to a batch at
        one of those locations - None means unrestricted. Delivery notes
        stay unscoped: they aren't attributable to a single warehouse
        location in this schema.
        """
        today = date.today()
        start_date = today - timedelta(days=days)

        # Get movements
        movements_query = select(Movement).where(
            func.date(Movement.timestamp) >= start_date
        )
        if location_ids is not None:
            movements_query = movements_query.join(Batch, Movement.batch_id == Batch.id).where(
                Batch.location_id.in_(location_ids)
            )
        result = await self.db.execute(movements_query)
        movements = result.scalars().all()

        receipts = sum(
            m.quantity for m in movements if m.movement_type == MovementType.RECEIPT
        )
        dispatches = sum(
            m.quantity for m in movements if m.movement_type == MovementType.DISPATCH
        )
        scraps = sum(
            m.quantity for m in movements if m.movement_type == MovementType.SCRAP
        )

        # Get delivery notes
        result = await self.db.execute(
            select(func.count(DeliveryNote.id))
            .where(func.date(DeliveryNote.created_at) >= start_date)
        )
        delivery_notes_count = result.scalar() or 0

        # Get new alerts (item-only alerts are excluded when scoped, same
        # convention as the alerts endpoint - they aren't attributable to
        # one location)
        alerts_query = select(func.count(Alert.id)).where(
            func.date(Alert.created_at) >= start_date
        )
        if location_ids is not None:
            alerts_query = alerts_query.join(Batch, Alert.batch_id == Batch.id).where(
                Batch.location_id.in_(location_ids)
            )
        result = await self.db.execute(alerts_query)
        alerts_count = result.scalar() or 0

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "receipts_quantity": float(receipts),
            "dispatches_quantity": float(dispatches),
            "scraps_quantity": float(scraps),
            "delivery_notes_created": delivery_notes_count,
            "alerts_generated": alerts_count,
            "movements_count": len(movements),
        }

    async def get_movement_trend(
        self, days: int = 7, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Get daily receipts/dispatches/scraps for the trailing period,
        zero-filled so a trend chart has no gaps on days without movements.
        Uses the same start_date window as get_recent_activity so both
        endpoints agree on what "last N days" covers.

        location_ids restricts to movements whose batch is at one of those
        locations - None means unrestricted.
        """
        today = date.today()
        start_date = today - timedelta(days=days)

        query = (
            select(
                func.date(Movement.timestamp).label("day"),
                Movement.movement_type,
                func.sum(Movement.quantity).label("total"),
            )
            .where(func.date(Movement.timestamp) >= start_date)
        )
        if location_ids is not None:
            query = query.join(Batch, Movement.batch_id == Batch.id).where(
                Batch.location_id.in_(location_ids)
            )
        query = query.group_by(func.date(Movement.timestamp), Movement.movement_type)

        result = await self.db.execute(query)

        # func.date() comes back as a str on SQLite (tests) but as a date
        # object on Postgres (asyncpg, used in prod) - normalize both.
        totals: Dict[date, Dict[MovementType, Decimal]] = {}
        for day, movement_type, total in result.all():
            if isinstance(day, str):
                day = date.fromisoformat(day)
            totals.setdefault(day, {})[movement_type] = total

        num_days = (today - start_date).days + 1
        series = []
        for offset in range(num_days):
            day = start_date + timedelta(days=offset)
            day_totals = totals.get(day, {})
            series.append({
                "date": day.isoformat(),
                "receipts": float(day_totals.get(MovementType.RECEIPT, 0)),
                "dispatches": float(day_totals.get(MovementType.DISPATCH, 0)),
                "scraps": float(day_totals.get(MovementType.SCRAP, 0)),
            })

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "series": series,
        }

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
        amounts_by_currency: Dict[str, float],
        usd_to_ils: Decimal,
        eur_to_ils: Decimal,
        try_to_ils: Decimal,
    ) -> Decimal:
        rates = {"ILS": Decimal("1"), "USD": usd_to_ils, "EUR": eur_to_ils, "TRY": try_to_ils}
        return sum(
            (Decimal(str(amount)) * rates.get(ccy, Decimal("1")) for ccy, amount in amounts_by_currency.items()),
            Decimal("0"),
        )

    async def get_kpi_summary(
        self, location_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """Get all KPIs for dashboard.

        Fetches Items+Batches once and derives inventory value, at-risk
        value, and low-stock counts from that single dataset, instead of
        calling get_inventory_value / get_low_stock_items /
        (the old private at-risk helper) independently - each of those
        used to re-run its own `select(Item).options(selectinload(...))`
        over the same rows.

        location_ids restricts everything below (batches, activity, unread
        alerts) to those locations - None means unrestricted. Delivery-note
        counts inside get_recent_activity stay unscoped (not location
        attributable in this schema).
        """
        today = date.today()

        result = await self.db.execute(
            select(Item).options(_items_batches_loader(location_ids))
        )
        items = result.scalars().all()

        totals_by_currency: Dict[str, Decimal] = {}
        at_risk_by_ccy: Dict[str, Decimal] = {}
        items_with_stock = 0
        low_stock_count = 0
        critical_low_stock_count = 0

        for item in items:
            ccy = item.currency or "ILS"
            active_qty = available_quantity(item, today)

            if active_qty > 0:
                items_with_stock += 1
                totals_by_currency[ccy] = totals_by_currency.get(ccy, Decimal("0")) + active_qty * item.cost_price

            for batch in item.batches:
                if is_active_and_unexpired(batch, today) and (batch.expiration_date - today).days <= 60:
                    at_risk_by_ccy[ccy] = (
                        at_risk_by_ccy.get(ccy, Decimal("0")) + batch.quantity_available * item.cost_price
                    )

            if active_qty < item.reorder_point:
                low_stock_count += 1
                if active_qty < item.min_stock:
                    critical_low_stock_count += 1

        inventory_totals = {ccy: float(v) for ccy, v in totals_by_currency.items()}
        at_risk_totals = {ccy: float(v) for ccy, v in at_risk_by_ccy.items()}

        activity = await self.get_recent_activity(location_ids=location_ids)

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

        # at_risk_percentage needs a single ratio, which needs converting
        # both sides to one currency first - previously this summed
        # risk_map's per-level "percentage" fields, which were themselves
        # computed from values mixed across currencies without conversion.
        usd_to_ils, eur_to_ils, try_to_ils = await self._get_fx_rates()
        inventory_total_ils = self._sum_in_ils(inventory_totals, usd_to_ils, eur_to_ils, try_to_ils)
        at_risk_total_ils = self._sum_in_ils(at_risk_totals, usd_to_ils, eur_to_ils, try_to_ils)
        at_risk_percentage = (
            round(float(at_risk_total_ils / inventory_total_ils) * 100, 1)
            if inventory_total_ils > 0
            else 0
        )

        return {
            "inventory_value_by_currency": inventory_totals,
            "items_in_stock": items_with_stock,
            "at_risk_value_by_currency": at_risk_totals,
            "at_risk_percentage": at_risk_percentage,
            "low_stock_items": low_stock_count,
            "critical_low_stock": critical_low_stock_count,
            "unread_alerts": unread_alerts,
            "recent_receipts": activity["receipts_quantity"],
            "recent_dispatches": activity["dispatches_quantity"],
        }
