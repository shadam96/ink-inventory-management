"""Tests for the dashboard's expiry timeline, stock coverage, attention list
and the history-based KPIs (value 30 days ago, write-off, turnover)."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.security import get_password_hash
from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.location import Location
from app.models.movement import Movement, MovementType
from app.models.user import User, UserRole
from app.services.dashboard_service import DashboardService

TODAY = date.today()


def days_ago(n: int) -> datetime:
    return datetime.combine(TODAY - timedelta(days=n), time(12, 0), tzinfo=timezone.utc)


@pytest.fixture
async def user(db_session):
    u = User(
        username="insights_user",
        email="insights@test.com",
        hashed_password="hashed",
        full_name="Insights",
        role=UserRole.WAREHOUSE_WORKER,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
def make(db_session, user):
    """Small factory for items, batches and movements."""

    class Factory:
        async def item(self, sku, cost="10", currency="ILS", unit="L", reorder_point=0, min_stock=0):
            it = Item(
                sku=sku,
                name=f"Ink {sku}",
                supplier="S",
                unit_of_measure=unit,
                cost_price=Decimal(cost),
                currency=currency,
                reorder_point=reorder_point,
                min_stock=min_stock,
            )
            db_session.add(it)
            await db_session.flush()
            return it

        async def batch(self, item, qty, expires_in, received_ago=100, status=BatchStatus.ACTIVE,
                        location=None, scrapped_ago=None, number=None):
            b = Batch(
                batch_number=number or f"{item.sku}-{expires_in}-{received_ago}-{qty}",
                item_id=item.id,
                location_id=location.id if location else None,
                receipt_date=TODAY - timedelta(days=received_ago),
                expiration_date=TODAY + timedelta(days=expires_in),
                quantity_received=Decimal(str(qty)),
                quantity_available=Decimal(str(qty)),
                status=status,
            )
            if scrapped_ago is not None:
                b.scrapped_at = days_ago(scrapped_ago)
            db_session.add(b)
            await db_session.flush()
            return b

        async def move(self, batch, kind, qty, ago, before=None):
            """Records a movement whose before/after reflect the sign of `kind`.
            Does not touch batch.quantity_available - tests set the batch's
            current quantity directly."""
            qty = Decimal(str(qty))
            before = Decimal(str(before)) if before is not None else Decimal("100")
            after = before + qty if kind == MovementType.RECEIPT else before - qty
            db_session.add(Movement(
                batch_id=batch.id,
                user_id=user.id,
                movement_type=kind,
                quantity=qty,
                quantity_before=before,
                quantity_after=after,
                timestamp=days_ago(ago),
            ))
            await db_session.flush()

    return Factory()


class TestExpiryTimeline:
    async def test_buckets_by_days_until_expiration(self, db_session, make):
        ils = await make.item("TL-ILS", cost="10", unit="L")
        usd = await make.item("TL-USD", cost="2", currency="USD", unit="KG")
        await make.batch(ils, 5, expires_in=-1)       # expired
        await make.batch(ils, 1, expires_in=0)        # expires today - still sellable, like inventory value
        await make.batch(ils, 2, expires_in=30)
        await make.batch(ils, 3, expires_in=31)
        await make.batch(ils, 4, expires_in=90)
        await make.batch(usd, 6, expires_in=91)
        await make.batch(usd, 7, expires_in=181)
        # Ignored: not active, or nothing left
        await make.batch(ils, 0, expires_in=10, status=BatchStatus.DEPLETED)
        await make.batch(ils, 9, expires_in=-5, status=BatchStatus.SCRAP)
        await make.batch(ils, 0, expires_in=12)

        result = await DashboardService(db_session).get_expiry_timeline()
        buckets = {b["key"]: b for b in result["buckets"]}

        assert [b["key"] for b in result["buckets"]] == [
            "expired", "d0_30", "d31_60", "d61_90", "d91_180", "d181_plus",
        ]
        assert buckets["expired"] == {
            "key": "expired", "value_by_currency": {"ILS": 50.0}, "quantity_by_unit": {"L": 5.0}, "batches": 1,
        }
        assert buckets["d0_30"]["value_by_currency"] == {"ILS": 30.0}
        assert buckets["d0_30"]["batches"] == 2
        assert buckets["d31_60"]["quantity_by_unit"] == {"L": 3.0}
        assert buckets["d61_90"]["value_by_currency"] == {"ILS": 40.0}
        assert buckets["d91_180"] == {
            "key": "d91_180", "value_by_currency": {"USD": 12.0}, "quantity_by_unit": {"KG": 6.0}, "batches": 1,
        }
        assert buckets["d181_plus"]["value_by_currency"] == {"USD": 14.0}

    async def test_scoped_to_locations(self, db_session, make):
        here = Location(warehouse="W", shelf="A", position="1", location_code="TL-A1")
        there = Location(warehouse="W", shelf="B", position="1", location_code="TL-B1")
        db_session.add_all([here, there])
        await db_session.flush()
        it = await make.item("TL-SCOPE")
        await make.batch(it, 5, expires_in=10, location=here)
        await make.batch(it, 7, expires_in=10, location=there)

        result = await DashboardService(db_session).get_expiry_timeline(location_ids=[here.id])
        d0_30 = next(b for b in result["buckets"] if b["key"] == "d0_30")

        assert d0_30["quantity_by_unit"] == {"L": 5.0}


class TestStockCoverage:
    async def test_days_of_supply_from_trailing_outbound(self, db_session, make):
        # A: 90-day usage = 30 + 15 dispatched + 9 consumed = 54 -> 0.6/day.
        # The 50 dispatched 100 days ago is outside the window, scrap never counts.
        a = await make.item("CV-A", reorder_point=20, min_stock=5)
        a_batch = await make.batch(a, 16, expires_in=200, received_ago=120)
        await make.move(a_batch, MovementType.DISPATCH, 50, ago=100)
        await make.move(a_batch, MovementType.DISPATCH, 15, ago=60)
        await make.move(a_batch, MovementType.DISPATCH, 30, ago=10)
        await make.move(a_batch, MovementType.CONSUMPTION, 9, ago=5)
        await make.move(a_batch, MovementType.SCRAP, 4, ago=3)
        await make.batch(a, 50, expires_in=-2)  # expired stock is not "on hand"

        # B: received 10 days ago -> usage averages over those 11 days
        # (today included), not 90.
        b = await make.item("CV-B", reorder_point=10)
        b_batch = await make.batch(b, 30, expires_in=200, received_ago=10)
        await make.move(b_batch, MovementType.DISPATCH, 20, ago=2)

        # C: stock but no demand.
        c = await make.item("CV-C", reorder_point=10)
        await make.batch(c, 40, expires_in=300, received_ago=200)

        # D: out of stock but still in demand.
        d = await make.item("CV-D", reorder_point=10, min_stock=5)
        d_batch = await make.batch(d, 0, expires_in=100, received_ago=150, status=BatchStatus.DEPLETED)
        await make.move(d_batch, MovementType.DISPATCH, 9, ago=30)

        result = await DashboardService(db_session).get_stock_coverage()
        rows = {r["sku"]: r for r in result["items"]}

        assert result["window_days"] == 90
        assert [r["sku"] for r in result["items"]] == ["CV-D", "CV-B", "CV-A", "CV-C"]

        assert rows["CV-A"]["quantity"] == 16.0
        assert rows["CV-A"]["avg_daily_usage"] == pytest.approx(0.6)
        assert rows["CV-A"]["days_of_supply"] == pytest.approx(16 / 0.6)
        assert rows["CV-A"]["status"] == "below_reorder"

        assert rows["CV-B"]["avg_daily_usage"] == pytest.approx(20 / 11)
        assert rows["CV-B"]["days_of_supply"] == pytest.approx(16.5)
        assert rows["CV-B"]["status"] == "ok"

        assert rows["CV-C"]["avg_daily_usage"] == 0
        assert rows["CV-C"]["days_of_supply"] is None

        assert rows["CV-D"]["quantity"] == 0
        assert rows["CV-D"]["days_of_supply"] == 0
        assert rows["CV-D"]["status"] == "out"

    async def test_out_of_stock_without_demand_has_zero_days(self, db_session, make):
        """Out of stock is urgent even with no recent usage - it must not
        read as "no demand"."""
        it = await make.item("CV-OUT", reorder_point=20)
        await make.batch(it, 0, expires_in=100, received_ago=200, status=BatchStatus.DEPLETED)

        result = await DashboardService(db_session).get_stock_coverage()

        assert result["items"][0]["days_of_supply"] == 0
        assert result["items"][0]["status"] == "out"

    async def test_item_with_nothing_to_report_is_omitted(self, db_session, make):
        await make.item("CV-IDLE")  # no stock, no demand, no reorder point

        result = await DashboardService(db_session).get_stock_coverage()

        assert result["items"] == []


class TestAttentionItems:
    async def test_lists_each_kind_of_exception(self, db_session, make):
        lots = await make.item("AT-LOTS", cost="10", min_stock=0)
        await make.batch(lots, 5, expires_in=-3, number="AT-EXPIRED")
        await make.batch(lots, 4, expires_in=25, number="AT-25")
        await make.batch(lots, 3, expires_in=10, number="AT-10")
        await make.batch(lots, 2, expires_in=40, number="AT-40")
        await make.batch(lots, 1, expires_in=-3, status=BatchStatus.SCRAP, number="AT-SCRAPPED")

        low = await make.item("AT-LOW", min_stock=5, reorder_point=10)
        await make.batch(low, 2, expires_in=200)
        empty = await make.item("AT-EMPTY", min_stock=5, reorder_point=10)
        fine = await make.item("AT-FINE", min_stock=5, reorder_point=10)
        await make.batch(fine, 8, expires_in=200)

        dead = await make.item("AT-DEAD")
        dead_batch = await make.batch(dead, 10, expires_in=300, received_ago=250)
        await make.move(dead_batch, MovementType.RECEIPT, 10, ago=250, before=0)
        # Never moved at all: the dead-stock alert skips these, so the
        # dashboard does too.
        unmoved = await make.item("AT-UNMOVED")
        await make.batch(unmoved, 10, expires_in=300, received_ago=250)
        alive = await make.item("AT-ALIVE")
        alive_batch = await make.batch(alive, 10, expires_in=300, received_ago=250)
        await make.move(alive_batch, MovementType.DISPATCH, 1, ago=10)

        result = await DashboardService(db_session).get_attention_items()

        assert [lot["batch_number"] for lot in result["expired_on_shelf"]] == ["AT-EXPIRED"]
        assert result["expired_on_shelf"][0]["days_until_expiration"] == -3
        assert result["expired_on_shelf"][0]["value"] == 50.0
        assert result["expired_on_shelf"][0]["currency"] == "ILS"
        assert [lot["batch_number"] for lot in result["expiring_soon"]] == ["AT-10", "AT-25"]

        below_min = {row["sku"]: row for row in result["below_min"]}
        assert set(below_min) == {"AT-LOW", "AT-EMPTY"}
        assert below_min["AT-EMPTY"]["quantity"] == 0
        assert below_min["AT-LOW"]["min_stock"] == 5

        assert [row["sku"] for row in result["dead_stock"]] == ["AT-DEAD"]
        assert result["dead_stock"][0]["days_inactive"] == 250
        assert result["dead_stock"][0]["quantity"] == 10.0


class TestHistoryKpis:
    async def test_inventory_value_30_days_ago_is_rebuilt_from_movements(self, db_session, make):
        it = await make.item("HK-VAL", cost="10")
        # Received 70 forty days ago, 20 dispatched ten days ago -> 50 now, 70 then.
        x = await make.batch(it, 50, expires_in=200, received_ago=40)
        await make.move(x, MovementType.RECEIPT, 70, ago=40, before=0)
        await make.move(x, MovementType.DISPATCH, 20, ago=10, before=70)
        # Received 5 days ago -> didn't exist 30 days ago.
        y = await make.batch(it, 30, expires_in=200, received_ago=5)
        await make.move(y, MovementType.RECEIPT, 30, ago=5, before=0)
        # Fully dispatched 20 days ago -> 0 now, 10 then.
        z = await make.batch(it, 0, expires_in=200, received_ago=50, status=BatchStatus.DEPLETED)
        await make.move(z, MovementType.RECEIPT, 10, ago=50, before=0)
        await make.move(z, MovementType.DISPATCH, 10, ago=20, before=10)
        # Expired 10 days ago -> excluded now, still good 30 days ago.
        await make.batch(it, 8, expires_in=-10, received_ago=100)

        kpis = await DashboardService(db_session).get_kpi_summary()

        assert kpis["inventory_value_by_currency"] == {"ILS": 800.0}
        assert kpis["inventory_value_30d_ago_by_currency"] == {"ILS": 880.0}

    async def test_scrapped_batch_counts_until_it_was_scrapped(self, db_session, make):
        it = await make.item("HK-SCRAP", cost="10")
        # Scrapping only flips status - quantity_available keeps what was written off.
        await make.batch(it, 6, expires_in=100, received_ago=60, status=BatchStatus.SCRAP, scrapped_ago=20)

        kpis = await DashboardService(db_session).get_kpi_summary()

        assert kpis["inventory_value_by_currency"] == {}
        assert kpis["inventory_value_30d_ago_by_currency"] == {"ILS": 60.0}

    async def test_write_off_counts_scrapped_batches_in_last_90_days(self, db_session, make):
        ils = await make.item("HK-WO", cost="10")
        usd = await make.item("HK-WO-USD", cost="5", currency="USD")
        await make.batch(ils, 6, expires_in=-21, received_ago=200, status=BatchStatus.SCRAP, scrapped_ago=20)
        # Scrapped 120 days ago, edited since - updated_at is today.
        await make.batch(ils, 99, expires_in=-130, received_ago=300, status=BatchStatus.SCRAP, scrapped_ago=120)
        await make.batch(usd, 2, expires_in=-5, received_ago=200, status=BatchStatus.SCRAP, scrapped_ago=4)
        # A SCRAP movement (partial write-off) counts too.
        partial = await make.batch(ils, 10, expires_in=200, received_ago=200)
        await make.move(partial, MovementType.SCRAP, 1, ago=7, before=11)

        kpis = await DashboardService(db_session).get_kpi_summary()

        assert kpis["write_off_90d_value_by_currency"] == {"ILS": 70.0, "USD": 10.0}

    async def test_turnover_and_days_on_hand(self, db_session, make):
        it = await make.item("HK-TURN", cost="10")
        b = await make.batch(it, 91, expires_in=300, received_ago=200)
        await make.move(b, MovementType.DISPATCH, 9, ago=10, before=100)

        kpis = await DashboardService(db_session).get_kpi_summary()

        # Average inventory = mean of value today/30/60/90 days ago = (910 + 3*1000) / 4.
        avg_inventory = 977.5
        assert kpis["avg_inventory_value_ils"] == pytest.approx(avg_inventory)
        assert kpis["turnover_annualized"] == pytest.approx(90 * 365 / 90 / avg_inventory, rel=1e-3)
        assert kpis["days_on_hand"] == pytest.approx(avg_inventory / (90 / 90), rel=1e-3)
        assert kpis["write_off_90d_rate"] == 0

    async def test_turnover_with_less_history_than_the_window(self, db_session, make):
        """40 days after the first receipt, outbound per day and average
        inventory cover those 41 days - not 90, half of them before any stock."""
        it = await make.item("HK-NEW", cost="10")
        b = await make.batch(it, 80, expires_in=300, received_ago=40)
        await make.move(b, MovementType.RECEIPT, 100, ago=40, before=0)
        await make.move(b, MovementType.DISPATCH, 20, ago=10, before=100)

        kpis = await DashboardService(db_session).get_kpi_summary()

        # Inventory now 800 and 30 days ago 1000; 60/90 days ago predate it.
        avg_inventory = 900
        daily_outbound = 200 / 41
        assert kpis["avg_inventory_value_ils"] == pytest.approx(avg_inventory)
        assert kpis["turnover_annualized"] == pytest.approx(daily_outbound * 365 / avg_inventory, rel=1e-3)
        assert kpis["days_on_hand"] == pytest.approx(avg_inventory / daily_outbound, rel=1e-3)

    async def test_no_outbound_means_zero_turnover_and_no_days_on_hand(self, db_session, make):
        it = await make.item("HK-IDLE", cost="10")
        await make.batch(it, 5, expires_in=300)

        kpis = await DashboardService(db_session).get_kpi_summary()

        assert kpis["turnover_annualized"] == 0
        assert kpis["days_on_hand"] is None


class TestScrappedAt:
    async def test_set_when_scrapped_and_kept_through_later_edits(self, db_session, make):
        it = await make.item("SA-1")
        b = await make.batch(it, 5, expires_in=100)
        assert b.scrapped_at is None

        b.status = BatchStatus.SCRAP
        scrapped_at = b.scrapped_at
        assert scrapped_at is not None

        b.status = BatchStatus.SCRAP  # e.g. a PUT echoing the current status
        b.notes = "edited later"
        assert b.scrapped_at == scrapped_at

        b.status = BatchStatus.ACTIVE
        assert b.scrapped_at is None


class TestMovementTrendConsumption:
    async def test_series_reports_consumption_separately(self, db_session, make):
        it = await make.item("MT-CON")
        b = await make.batch(it, 10, expires_in=100)
        await make.move(b, MovementType.CONSUMPTION, 3, ago=1)
        await make.move(b, MovementType.DISPATCH, 2, ago=1)

        trend = await DashboardService(db_session).get_movement_trend(days=3)
        point = next(p for p in trend["series"] if p["date"] == (TODAY - timedelta(days=1)).isoformat())

        assert point["consumptions"] == 3.0
        assert point["dispatches"] == 2.0

    async def test_series_reports_value_per_currency(self, db_session, make):
        """Quantities can't be summed across liters and kilograms, so each
        day also carries cost value, bucketed by item currency."""
        ils = await make.item("MT-ILS", cost="10", unit="L")
        usd = await make.item("MT-USD", cost="4", currency="USD", unit="KG")
        a = await make.batch(ils, 10, expires_in=100)
        b = await make.batch(usd, 10, expires_in=100)
        await make.move(a, MovementType.RECEIPT, 5, ago=0)
        await make.move(a, MovementType.DISPATCH, 2, ago=0)
        await make.move(b, MovementType.CONSUMPTION, 3, ago=0)
        await make.move(b, MovementType.SCRAP, 1, ago=0)

        trend = await DashboardService(db_session).get_movement_trend(days=1)
        point = next(p for p in trend["series"] if p["date"] == TODAY.isoformat())

        assert point["receipts_value_by_currency"] == {"ILS": 50.0}
        assert point["outbound_value_by_currency"] == {"ILS": 20.0, "USD": 12.0}


class TestInsightsAPI:
    @pytest.fixture
    async def auth_headers(self, client, db_session):
        db_session.add(User(
            username="insights_viewer",
            email="insights_viewer@test.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Insights Viewer",
            role=UserRole.VIEWER,
            is_active=True,
        ))
        await db_session.commit()
        response = await client.post("/api/v1/auth/login", json={
            "username": "insights_viewer",
            "password": "testpass123",
        })
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    async def test_expiry_timeline_api(self, client, auth_headers):
        response = await client.get("/api/v1/dashboard/expiry-timeline", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["buckets"]) == 6

    async def test_stock_coverage_api(self, client, auth_headers):
        response = await client.get("/api/v1/dashboard/stock-coverage", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"window_days": 90, "items": []}

    async def test_attention_api(self, client, auth_headers):
        response = await client.get("/api/v1/dashboard/attention", headers=auth_headers)
        assert response.status_code == 200
        assert set(response.json()) == {"expired_on_shelf", "expiring_soon", "below_min", "dead_stock"}

    async def test_kpis_api_includes_history_fields(self, client, auth_headers):
        response = await client.get("/api/v1/dashboard/kpis", headers=auth_headers)
        assert response.status_code == 200
        assert {
            "inventory_value_30d_ago_by_currency",
            "write_off_90d_value_by_currency",
            "write_off_90d_rate",
            "turnover_annualized",
            "days_on_hand",
        } <= response.json().keys()

    async def test_new_endpoints_require_auth(self, client):
        for path in ("expiry-timeline", "stock-coverage", "attention"):
            response = await client.get(f"/api/v1/dashboard/{path}")
            assert response.status_code in (401, 403)
