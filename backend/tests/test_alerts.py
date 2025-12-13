"""Tests for alert service functionality"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.user import User
from app.services.alert_service import AlertService
from app.core.security import get_password_hash


class TestAlertService:
    """Test alert service"""
    
    @pytest.fixture
    async def sample_item(self, db_session):
        """Create a sample item"""
        item = Item(
            sku="ALERT-INK-001",
            name="דיו התראות",
            supplier="ספק בדיקה",
            unit_of_measure="ליטר",
            cost_price=Decimal("75.00"),
            min_stock=5,
            reorder_point=15,
        )
        db_session.add(item)
        await db_session.flush()
        return item
    
    async def test_create_alert(self, db_session, sample_item):
        """Test creating an alert"""
        service = AlertService(db_session)
        
        alert = await service.create_alert(
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.WARNING,
            title="מלאי נמוך",
            message="מלאי דיו נמוך",
            item_id=sample_item.id,
        )
        
        assert alert.id is not None
        assert alert.alert_type == AlertType.LOW_STOCK
        assert alert.severity == AlertSeverity.WARNING
        assert alert.is_read is False
        assert alert.is_dismissed is False
    
    async def test_get_unread_alerts(self, db_session, sample_item):
        """Test getting unread alerts"""
        service = AlertService(db_session)
        
        # Create some alerts
        await service.create_alert(
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.WARNING,
            title="Alert 1",
            message="Message 1",
            item_id=sample_item.id,
        )
        alert2 = await service.create_alert(
            alert_type=AlertType.EXPIRATION_WARNING,
            severity=AlertSeverity.CRITICAL,
            title="Alert 2",
            message="Message 2",
        )
        await db_session.flush()
        
        # Mark one as read
        alert2.is_read = True
        await db_session.flush()
        
        unread = await service.get_unread_alerts()
        
        assert len(unread) == 1
        assert unread[0].title == "Alert 1"
    
    async def test_get_unread_count(self, db_session):
        """Test counting unread alerts"""
        service = AlertService(db_session)
        
        # Create alerts
        for i in range(5):
            await service.create_alert(
                alert_type=AlertType.LOW_STOCK,
                severity=AlertSeverity.INFO,
                title=f"Alert {i}",
                message=f"Message {i}",
            )
        await db_session.flush()
        
        count = await service.get_unread_count()
        assert count == 5
    
    async def test_mark_as_read(self, db_session):
        """Test marking alert as read"""
        service = AlertService(db_session)
        
        alert = await service.create_alert(
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.INFO,
            title="Test Alert",
            message="Test message",
        )
        await db_session.flush()
        
        await service.mark_as_read(alert.id)
        await db_session.refresh(alert)
        
        assert alert.is_read is True
    
    async def test_mark_all_as_read(self, db_session):
        """Test marking all alerts as read"""
        service = AlertService(db_session)
        
        # Create unread alerts
        for i in range(3):
            await service.create_alert(
                alert_type=AlertType.LOW_STOCK,
                severity=AlertSeverity.INFO,
                title=f"Alert {i}",
                message=f"Message {i}",
            )
        await db_session.flush()
        
        count = await service.mark_all_as_read()
        
        assert count == 3
        
        # Verify all are read
        unread = await service.get_unread_count()
        assert unread == 0
    
    async def test_dismiss_alert(self, db_session):
        """Test dismissing an alert"""
        service = AlertService(db_session)
        
        alert = await service.create_alert(
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.INFO,
            title="Test Alert",
            message="Test message",
        )
        await db_session.flush()
        
        await service.dismiss_alert(alert.id)
        await db_session.refresh(alert)
        
        assert alert.is_dismissed is True
    
    async def test_check_expiring_batches(self, db_session, sample_item):
        """Test checking for expiring batches"""
        service = AlertService(db_session)
        
        # Create batch expiring in 25 days (critical)
        batch = Batch(
            batch_number="EXP-BATCH-001",
            item_id=sample_item.id,
            expiration_date=date.today() + timedelta(days=25),
            receipt_date=date.today(),
            quantity_received=Decimal("50.00"),
            quantity_available=Decimal("50.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch)
        await db_session.flush()
        
        alerts = await service.check_expiring_batches()
        
        # Should create at least one alert
        assert len(alerts) >= 1
        
        # Verify alert details
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical_alerts) >= 1
    
    async def test_check_expired_batches(self, db_session, sample_item):
        """Test checking and marking expired batches"""
        service = AlertService(db_session)
        
        # Create already expired batch
        batch = Batch(
            batch_number="EXPIRED-BATCH-001",
            item_id=sample_item.id,
            expiration_date=date.today() - timedelta(days=5),
            receipt_date=date.today() - timedelta(days=100),
            quantity_received=Decimal("30.00"),
            quantity_available=Decimal("30.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch)
        await db_session.flush()
        
        results = await service.check_expired_batches()
        
        assert len(results) == 1
        expired_batch, alert = results[0]
        
        # Batch should be marked as scrap
        assert expired_batch.status == BatchStatus.SCRAP
        assert "גריטה" in expired_batch.notes
        
        # Alert should be created
        assert alert.alert_type == AlertType.EXPIRED
        assert alert.severity == AlertSeverity.CRITICAL
    
    async def test_check_low_stock(self, db_session):
        """Test checking for low stock items"""
        service = AlertService(db_session)
        
        # Create item with high reorder point
        item = Item(
            sku="LOW-STOCK-001",
            name="Low Stock Item",
            supplier="Test Supplier",
            unit_of_measure="kg",
            cost_price=Decimal("100.00"),
            min_stock=10,
            reorder_point=50,
        )
        db_session.add(item)
        await db_session.flush()
        
        # Create batch with small quantity
        batch = Batch(
            batch_number="LOW-BT-001",
            item_id=item.id,
            expiration_date=date.today() + timedelta(days=180),
            receipt_date=date.today(),
            quantity_received=Decimal("20.00"),
            quantity_available=Decimal("20.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch)
        await db_session.flush()
        
        alerts = await service.check_low_stock()
        
        # Should have alert for item below reorder point
        assert len(alerts) >= 1
        low_stock_alert = next(
            (a for a in alerts if a.item_id == item.id), None
        )
        assert low_stock_alert is not None
        assert low_stock_alert.alert_type == AlertType.LOW_STOCK
    
    async def test_run_all_checks(self, db_session, sample_item):
        """Test running all alert checks"""
        service = AlertService(db_session)
        
        # Create various scenarios
        # Expiring batch
        batch1 = Batch(
            batch_number="CHECK-ALL-001",
            item_id=sample_item.id,
            expiration_date=date.today() + timedelta(days=20),
            receipt_date=date.today(),
            quantity_received=Decimal("100.00"),
            quantity_available=Decimal("100.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch1)
        await db_session.flush()
        
        result = await service.run_all_checks()
        
        assert "expiring_alerts" in result
        assert "expired_batches" in result
        assert "low_stock_alerts" in result
        assert "dead_stock_alerts" in result
        assert "total_new_alerts" in result


class TestAlertsAPI:
    """Test alerts API endpoints"""
    
    @pytest.fixture
    async def auth_token(self, client, db_session):
        """Get auth token for manager user"""
        from app.models.user import UserRole
        
        user = User(
            username="alert_manager",
            email="alert_manager@test.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Alert Manager",
            role=UserRole.MANAGER,
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        
        response = await client.post("/api/v1/auth/login", json={
            "username": "alert_manager",
            "password": "testpass123",
        })
        return response.json()["access_token"]
    
    async def test_get_alerts_summary_empty(self, client, auth_token):
        """Test getting alerts summary when empty"""
        response = await client.get(
            "/api/v1/alerts/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_unread"] == 0
    
    async def test_list_alerts(self, client, auth_token, db_session):
        """Test listing alerts"""
        # Create some alerts
        service = AlertService(db_session)
        for i in range(3):
            await service.create_alert(
                alert_type=AlertType.LOW_STOCK,
                severity=AlertSeverity.WARNING,
                title=f"Test Alert {i}",
                message=f"Test message {i}",
            )
        await db_session.commit()
        
        response = await client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
    
    async def test_mark_alert_read_api(self, client, auth_token, db_session):
        """Test marking alert as read via API"""
        service = AlertService(db_session)
        alert = await service.create_alert(
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.INFO,
            title="Test Alert",
            message="Test message",
        )
        await db_session.commit()
        
        response = await client.put(
            f"/api/v1/alerts/{alert.id}/read",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    async def test_mark_all_read_api(self, client, auth_token, db_session):
        """Test marking all alerts as read via API"""
        service = AlertService(db_session)
        for i in range(5):
            await service.create_alert(
                alert_type=AlertType.LOW_STOCK,
                severity=AlertSeverity.INFO,
                title=f"Alert {i}",
                message=f"Message {i}",
            )
        await db_session.commit()
        
        response = await client.put(
            "/api/v1/alerts/read-all",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["marked_count"] == 5
    
    async def test_run_checks_api(self, client, auth_token):
        """Test running alert checks via API"""
        response = await client.post(
            "/api/v1/alerts/run-checks",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "results" in data
