"""Tests for dashboard service functionality"""
import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from app.models.movement import Movement, MovementType
from app.models.user import User
from app.services.dashboard_service import DashboardService
from app.core.security import get_password_hash


class TestDashboardService:
    """Test dashboard service"""
    
    @pytest.fixture
    async def sample_items_with_batches(self, db_session):
        """Create sample items with batches for dashboard testing"""
        items = []
        
        # Item 1: Expensive ink with safe expiration
        item1 = Item(
            sku="DASH-INK-001",
            name="Premium Black Ink",
            supplier="Premium Supplier",
            unit_of_measure="ליטר",
            cost_price=Decimal("200.00"),
            min_stock=5,
            reorder_point=20,
        )
        db_session.add(item1)
        
        # Item 2: Cheaper ink with critical expiration
        item2 = Item(
            sku="DASH-INK-002",
            name="Standard Cyan Ink",
            supplier="Standard Supplier",
            unit_of_measure="ליטר",
            cost_price=Decimal("100.00"),
            min_stock=10,
            reorder_point=30,
        )
        db_session.add(item2)
        
        await db_session.flush()
        
        # Batches for item1
        batch1 = Batch(
            batch_number="DASH-BT-001",
            item_id=item1.id,
            expiration_date=date.today() + timedelta(days=180),  # Safe
            receipt_date=date.today(),
            quantity_received=Decimal("100.00"),
            quantity_available=Decimal("50.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch1)
        
        # Batches for item2 - critical expiration
        batch2 = Batch(
            batch_number="DASH-BT-002",
            item_id=item2.id,
            expiration_date=date.today() + timedelta(days=15),  # Critical
            receipt_date=date.today(),
            quantity_received=Decimal("80.00"),
            quantity_available=Decimal("40.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch2)
        
        # Another batch for item2 - warning expiration  
        batch3 = Batch(
            batch_number="DASH-BT-003",
            item_id=item2.id,
            expiration_date=date.today() + timedelta(days=45),  # Warning
            receipt_date=date.today(),
            quantity_received=Decimal("60.00"),
            quantity_available=Decimal("60.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch3)
        
        await db_session.flush()
        
        return {
            "items": [item1, item2],
            "batches": [batch1, batch2, batch3],
        }
    
    async def test_kpi_inventory_value(self, db_session, sample_items_with_batches):
        """Inventory value is bucketed by per-item currency."""
        kpis = await DashboardService(db_session).get_kpi_summary()

        # Both fixture items default to ILS — totals collapse into one bucket.
        # Item1: 50 * 200 = 10,000; Item2: (40 + 60) * 100 = 10,000 → ILS 20,000.
        assert kpis["inventory_value_by_currency"] == {"ILS": 20000.0}
        assert kpis["items_in_stock"] == 2

    async def test_kpi_inventory_value_buckets_distinct_currencies(
        self, db_session, sample_items_with_batches
    ):
        """A USD-priced item must not be summed with ILS items."""
        usd_item = Item(
            sku="DASH-INK-USD",
            name="Imported Ink",
            supplier="US Supplier",
            unit_of_measure="ליטר",
            cost_price=Decimal("50.00"),
            currency="USD",
            min_stock=0,
            reorder_point=0,
        )
        db_session.add(usd_item)
        await db_session.flush()
        db_session.add(
            Batch(
                batch_number="DASH-BT-USD",
                item_id=usd_item.id,
                expiration_date=date.today() + timedelta(days=180),
                receipt_date=date.today(),
                quantity_received=Decimal("10"),
                quantity_available=Decimal("10"),
                status=BatchStatus.ACTIVE,
            )
        )
        await db_session.flush()

        kpis = await DashboardService(db_session).get_kpi_summary()

        assert kpis["inventory_value_by_currency"] == {"ILS": 20000.0, "USD": 500.0}

    async def test_kpi_low_stock_counts(self, db_session):
        """Below reorder point counts as low stock; below min_stock also
        counts as critical."""
        critical = Item(
            sku="LOW-DASH-001",
            name="Below Minimum",
            supplier="Test Supplier",
            unit_of_measure="kg",
            cost_price=Decimal("50.00"),
            min_stock=20,
            reorder_point=50,
        )
        low = Item(
            sku="LOW-DASH-002",
            name="Below Reorder Point",
            supplier="Test Supplier",
            unit_of_measure="kg",
            cost_price=Decimal("50.00"),
            min_stock=10,
            reorder_point=50,
        )
        db_session.add_all([critical, low])
        await db_session.flush()
        for item, qty in ((critical, "15"), (low, "30")):
            db_session.add(Batch(
                batch_number=f"{item.sku}-BT",
                item_id=item.id,
                expiration_date=date.today() + timedelta(days=180),
                receipt_date=date.today(),
                quantity_received=Decimal(qty),
                quantity_available=Decimal(qty),
                status=BatchStatus.ACTIVE,
            ))
        await db_session.flush()

        kpis = await DashboardService(db_session).get_kpi_summary()

        assert kpis["low_stock_items"] == 2
        assert kpis["critical_low_stock"] == 1

    async def test_get_movement_trend(self, db_session, sample_items_with_batches):
        """Trend series must be zero-filled for every day in range and
        bucket movements onto the correct day, not just summed overall."""
        service = DashboardService(db_session)
        batches = sample_items_with_batches["batches"]

        from app.models.user import UserRole

        user = User(
            username="trend_test_user",
            email="trend_test@test.com",
            hashed_password="hashed",
            full_name="Trend Test",
            role=UserRole.WAREHOUSE_WORKER,
        )
        db_session.add(user)
        await db_session.flush()

        today = datetime.now(timezone.utc)
        two_days_ago = today - timedelta(days=2)

        db_session.add_all([
            Movement(
                batch_id=batches[0].id,
                user_id=user.id,
                movement_type=MovementType.RECEIPT,
                quantity=Decimal("10.00"),
                quantity_before=Decimal("0.00"),
                quantity_after=Decimal("10.00"),
                timestamp=today,
            ),
            Movement(
                batch_id=batches[0].id,
                user_id=user.id,
                movement_type=MovementType.DISPATCH,
                quantity=Decimal("4.00"),
                quantity_before=Decimal("10.00"),
                quantity_after=Decimal("6.00"),
                timestamp=two_days_ago,
            ),
        ])
        await db_session.flush()

        trend = await service.get_movement_trend(days=3)

        # A 3-day window is the 3 days up to and including today
        assert trend["period_days"] == 3
        assert len(trend["series"]) == 3

        by_date = {point["date"]: point for point in trend["series"]}
        assert by_date[today.date().isoformat()]["receipts"] == 10.0
        assert by_date[today.date().isoformat()]["dispatches"] == 0.0
        assert by_date[two_days_ago.date().isoformat()]["dispatches"] == 4.0

        # A day with no movements must still be present, zero-filled.
        no_movement_day = (two_days_ago + timedelta(days=1)).date().isoformat()
        assert by_date[no_movement_day]["receipts"] == 0.0
        assert by_date[no_movement_day]["dispatches"] == 0.0
        assert by_date[no_movement_day]["scraps"] == 0.0

    async def test_get_kpi_summary(self, db_session, sample_items_with_batches):
        """Test getting complete KPI summary"""
        service = DashboardService(db_session)

        kpis = await service.get_kpi_summary()

        # Verify all KPIs present
        assert "inventory_value_by_currency" in kpis
        assert "items_in_stock" in kpis
        assert "low_stock_items" in kpis
        assert "unread_alerts" in kpis

        # Verify values are reasonable
        assert sum(kpis["inventory_value_by_currency"].values()) > 0
        assert kpis["items_in_stock"] >= 2


class TestDashboardAPI:
    """Test dashboard API endpoints"""
    
    @pytest.fixture
    async def auth_token(self, client, db_session):
        """Get auth token for viewer user"""
        from app.models.user import UserRole
        
        user = User(
            username="dashboard_viewer",
            email="dashboard_viewer@test.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Dashboard Viewer",
            role=UserRole.VIEWER,
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        
        response = await client.post("/api/v1/auth/login", json={
            "username": "dashboard_viewer",
            "password": "testpass123",
        })
        return response.json()["access_token"]
    
    async def test_get_kpis_api(self, client, auth_token):
        """Test getting KPIs via API"""
        response = await client.get(
            "/api/v1/dashboard/kpis",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "inventory_value_by_currency" in data

    async def test_get_movement_trend_api(self, client, auth_token):
        """Test getting movement trend via API"""
        response = await client.get(
            "/api/v1/dashboard/movement-trend?days=14",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 14
        assert len(data["series"]) == 14
        assert all(
            {"date", "receipts", "dispatches", "scraps"} <= point.keys()
            for point in data["series"]
        )

    async def test_unauthorized_access(self, client):
        """Test that unauthorized access is blocked"""
        response = await client.get("/api/v1/dashboard/kpis")
        
        # 401 or 403 both acceptable for unauthorized
        assert response.status_code in [401, 403]
