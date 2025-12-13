"""Tests for dashboard service functionality"""
import pytest
from datetime import date, timedelta
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
    
    async def test_get_inventory_value(self, db_session, sample_items_with_batches):
        """Test calculating inventory value"""
        service = DashboardService(db_session)
        
        result = await service.get_inventory_value()
        
        # Item1: 50 * 200 = 10,000
        # Item2: (40 + 60) * 100 = 10,000
        # Total: 20,000
        assert result["total_value"] == 20000.0
        assert result["total_quantity"] == 150.0  # 50 + 40 + 60
        assert result["items_with_stock"] == 2
        assert result["currency"] == "ILS"
    
    async def test_get_inventory_distribution(self, db_session, sample_items_with_batches):
        """Test inventory distribution"""
        service = DashboardService(db_session)
        
        distribution = await service.get_inventory_distribution()
        
        assert len(distribution) == 2
        
        # Should be sorted by value descending
        assert distribution[0]["value"] >= distribution[1]["value"]
        
        # Verify SKUs exist
        skus = [d["sku"] for d in distribution]
        assert "DASH-INK-001" in skus
        assert "DASH-INK-002" in skus
    
    async def test_get_expiration_risk_map(self, db_session, sample_items_with_batches):
        """Test expiration risk map"""
        service = DashboardService(db_session)
        
        result = await service.get_expiration_risk_map()
        
        risk_levels = result["risk_levels"]
        
        # Should have all risk levels
        assert "expired" in risk_levels
        assert "critical" in risk_levels
        assert "warning" in risk_levels
        assert "caution" in risk_levels
        assert "safe" in risk_levels
        
        # Should have color codes
        assert "color_codes" in result
        
        # Critical should have value (batch2 with 15 days)
        assert risk_levels["critical"]["batches"] >= 1
        
        # Safe should have value (batch1 with 180 days)
        assert risk_levels["safe"]["batches"] >= 1
    
    async def test_get_low_stock_items(self, db_session):
        """Test getting low stock items"""
        service = DashboardService(db_session)
        
        # Create item with high reorder point
        item = Item(
            sku="LOW-DASH-001",
            name="Low Stock Dashboard Test",
            supplier="Test Supplier",
            unit_of_measure="kg",
            cost_price=Decimal("50.00"),
            min_stock=20,
            reorder_point=50,
        )
        db_session.add(item)
        await db_session.flush()
        
        # Create batch with small quantity
        batch = Batch(
            batch_number="LOW-DASH-BT-001",
            item_id=item.id,
            expiration_date=date.today() + timedelta(days=180),
            receipt_date=date.today(),
            quantity_received=Decimal("15.00"),
            quantity_available=Decimal("15.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch)
        await db_session.flush()
        
        low_stock = await service.get_low_stock_items()
        
        # Should find our low stock item
        our_item = next(
            (i for i in low_stock if i["sku"] == "LOW-DASH-001"), None
        )
        assert our_item is not None
        assert our_item["current_quantity"] == 15.0
        assert our_item["reorder_point"] == 50
        assert our_item["shortage"] == 35.0
        assert our_item["is_critical"] is True  # Below min_stock of 20
    
    async def test_get_recent_activity(self, db_session, sample_items_with_batches):
        """Test getting recent activity"""
        service = DashboardService(db_session)
        
        batches = sample_items_with_batches["batches"]
        
        # Create a user for movements
        from app.models.user import UserRole
        
        user = User(
            username="activity_test_user",
            email="activity_test@test.com",
            hashed_password="hashed",
            full_name="Activity Test",
            role=UserRole.WAREHOUSE_WORKER,
        )
        db_session.add(user)
        await db_session.flush()
        
        # Create some movements
        for i, batch in enumerate(batches):
            movement = Movement(
                batch_id=batch.id,
                user_id=user.id,
                movement_type=MovementType.RECEIPT if i == 0 else MovementType.DISPATCH,
                quantity=Decimal("10.00"),
                quantity_before=Decimal("0.00") if i == 0 else batch.quantity_available,
                quantity_after=Decimal("10.00") if i == 0 else batch.quantity_available - Decimal("10.00"),
                reference_number=f"REF-{i:03d}",
            )
            db_session.add(movement)
        await db_session.flush()
        
        activity = await service.get_recent_activity(days=7)
        
        assert activity["period_days"] == 7
        assert activity["movements_count"] >= 3
        assert "receipts_quantity" in activity
        assert "dispatches_quantity" in activity
    
    async def test_get_kpi_summary(self, db_session, sample_items_with_batches):
        """Test getting complete KPI summary"""
        service = DashboardService(db_session)
        
        kpis = await service.get_kpi_summary()
        
        # Verify all KPIs present
        assert "inventory_value" in kpis
        assert "items_in_stock" in kpis
        assert "at_risk_value" in kpis
        assert "at_risk_percentage" in kpis
        assert "low_stock_items" in kpis
        assert "unread_alerts" in kpis
        assert "recent_receipts" in kpis
        assert "recent_dispatches" in kpis
        
        # Verify values are reasonable
        assert kpis["inventory_value"] > 0
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
        assert "inventory_value" in data
    
    async def test_get_inventory_value_api(self, client, auth_token):
        """Test getting inventory value via API"""
        response = await client.get(
            "/api/v1/dashboard/inventory-value",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "currency" in data
    
    async def test_get_inventory_distribution_api(self, client, auth_token):
        """Test getting inventory distribution via API"""
        response = await client.get(
            "/api/v1/dashboard/inventory-distribution",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    async def test_get_expiration_risk_api(self, client, auth_token):
        """Test getting expiration risk via API"""
        response = await client.get(
            "/api/v1/dashboard/expiration-risk",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_levels" in data
        assert "color_codes" in data
    
    async def test_get_low_stock_api(self, client, auth_token):
        """Test getting low stock items via API"""
        response = await client.get(
            "/api/v1/dashboard/low-stock",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "count" in data
    
    async def test_get_recent_activity_api(self, client, auth_token):
        """Test getting recent activity via API"""
        response = await client.get(
            "/api/v1/dashboard/recent-activity?days=14",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 14
        assert "movements_count" in data
    
    async def test_unauthorized_access(self, client):
        """Test that unauthorized access is blocked"""
        response = await client.get("/api/v1/dashboard/kpis")
        
        # 401 or 403 both acceptable for unauthorized
        assert response.status_code in [401, 403]
