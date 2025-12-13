"""Tests for delivery notes functionality"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from app.models.customer import Customer
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem, DeliveryNoteStatus
from app.models.user import User
from app.services.document_service import DocumentService
from app.core.security import get_password_hash


class TestDocumentService:
    """Test document service"""
    
    @pytest.fixture
    async def sample_customer(self, db_session):
        """Create a sample customer"""
        customer = Customer(
            name="לקוח בדיקה",
            address="רחוב הבדיקה 1, תל אביב",
            contact_person="יוסי ישראלי",
            phone="050-1234567",
            email="test@example.com",
        )
        db_session.add(customer)
        await db_session.flush()
        return customer
    
    @pytest.fixture
    async def sample_item(self, db_session):
        """Create a sample item"""
        item = Item(
            sku="INK-TEST-001",
            name="דיו בדיקה שחור",
            description="דיו לבדיקות",
            supplier="ספק בדיקה",
            unit_of_measure="ליטר",
            cost_price=Decimal("100.00"),
            min_stock=10,
            reorder_point=20,
        )
        db_session.add(item)
        await db_session.flush()
        return item
    
    @pytest.fixture
    async def sample_batch(self, db_session, sample_item):
        """Create a sample batch"""
        batch = Batch(
            batch_number="BT-2024-001",
            item_id=sample_item.id,
            expiration_date=date.today() + timedelta(days=180),
            receipt_date=date.today(),
            quantity_received=Decimal("100.00"),
            quantity_available=Decimal("100.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch)
        await db_session.flush()
        return batch
    
    @pytest.fixture
    async def sample_user(self, db_session):
        """Create a sample user"""
        from app.models.user import UserRole
        
        user = User(
            username="warehouse_test",
            email="warehouse@test.com",
            hashed_password="hashed_password",
            full_name="משתמש מחסן",
            role=UserRole.WAREHOUSE_WORKER,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        return user
    
    async def test_generate_delivery_note_number(self, db_session):
        """Test DN number generation"""
        service = DocumentService(db_session)
        
        dn_number = await service.generate_delivery_note_number()
        
        assert dn_number.startswith("DN-")
        assert len(dn_number.split("-")) == 3
    
    async def test_generate_unique_delivery_note_numbers(self, db_session, sample_customer, sample_batch, sample_user):
        """Test that sequential DN numbers are unique"""
        service = DocumentService(db_session)
        
        # Create first DN
        dn1 = await service.create_delivery_note(
            customer_id=sample_customer.id,
            items=[{"batch_id": sample_batch.id, "quantity": Decimal("10")}],
            user_id=sample_user.id,
        )
        await db_session.flush()
        
        # Create second DN
        dn2 = await service.create_delivery_note(
            customer_id=sample_customer.id,
            items=[{"batch_id": sample_batch.id, "quantity": Decimal("5")}],
            user_id=sample_user.id,
        )
        
        assert dn1.delivery_note_number != dn2.delivery_note_number
    
    async def test_create_delivery_note(self, db_session, sample_customer, sample_batch, sample_user):
        """Test creating a delivery note"""
        service = DocumentService(db_session)
        
        dn = await service.create_delivery_note(
            customer_id=sample_customer.id,
            items=[{"batch_id": sample_batch.id, "quantity": Decimal("25")}],
            user_id=sample_user.id,
            notes="הערות בדיקה",
        )
        
        assert dn.id is not None
        assert dn.customer_id == sample_customer.id
        assert dn.status == DeliveryNoteStatus.DRAFT
        assert dn.notes == "הערות בדיקה"
    
    async def test_create_consignment_delivery_note(self, db_session, sample_customer, sample_batch, sample_user):
        """Test creating a consignment delivery note"""
        service = DocumentService(db_session)
        
        dn = await service.create_delivery_note(
            customer_id=sample_customer.id,
            items=[{"batch_id": sample_batch.id, "quantity": Decimal("10")}],
            user_id=sample_user.id,
            is_consignment=True,
        )
        
        assert dn.is_consignment is True
    
    async def test_create_delivery_note_invalid_customer(self, db_session, sample_batch, sample_user):
        """Test creating DN with invalid customer"""
        service = DocumentService(db_session)
        
        with pytest.raises(ValueError, match="לקוח לא נמצא"):
            await service.create_delivery_note(
                customer_id=uuid4(),
                items=[{"batch_id": sample_batch.id, "quantity": Decimal("10")}],
                user_id=sample_user.id,
            )
    
    async def test_create_delivery_note_invalid_batch(self, db_session, sample_customer, sample_user):
        """Test creating DN with invalid batch"""
        service = DocumentService(db_session)
        
        with pytest.raises(ValueError, match="אצווה לא נמצאה"):
            await service.create_delivery_note(
                customer_id=sample_customer.id,
                items=[{"batch_id": uuid4(), "quantity": Decimal("10")}],
                user_id=sample_user.id,
            )
    
    async def test_get_delivery_note_with_details(self, db_session, sample_customer, sample_batch, sample_user):
        """Test retrieving DN with all details"""
        service = DocumentService(db_session)
        
        dn = await service.create_delivery_note(
            customer_id=sample_customer.id,
            items=[{"batch_id": sample_batch.id, "quantity": Decimal("15")}],
            user_id=sample_user.id,
        )
        await db_session.flush()
        
        dn_with_details = await service.get_delivery_note_with_details(dn.id)
        
        assert dn_with_details is not None
        assert dn_with_details.customer is not None
        assert len(dn_with_details.items) == 1
    
    async def test_update_delivery_note_status(self, db_session, sample_customer, sample_batch, sample_user):
        """Test updating DN status"""
        service = DocumentService(db_session)
        
        dn = await service.create_delivery_note(
            customer_id=sample_customer.id,
            items=[{"batch_id": sample_batch.id, "quantity": Decimal("10")}],
            user_id=sample_user.id,
        )
        await db_session.flush()
        
        # Update to issued
        dn = await service.update_delivery_note_status(
            dn.id, DeliveryNoteStatus.ISSUED
        )
        
        assert dn.status == DeliveryNoteStatus.ISSUED
        assert dn.issue_date is not None
        
        # Update to delivered
        dn = await service.update_delivery_note_status(
            dn.id, DeliveryNoteStatus.DELIVERED
        )
        
        assert dn.status == DeliveryNoteStatus.DELIVERED
        assert dn.delivery_date is not None
    
    async def test_update_nonexistent_delivery_note_status(self, db_session):
        """Test updating status of non-existent DN"""
        service = DocumentService(db_session)
        
        with pytest.raises(ValueError, match="תעודת משלוח לא נמצאה"):
            await service.update_delivery_note_status(
                uuid4(), DeliveryNoteStatus.ISSUED
            )
    
    async def test_generate_delivery_note_pdf(self, db_session, sample_customer, sample_batch, sample_user, sample_item):
        """Test PDF generation"""
        service = DocumentService(db_session)
        
        dn = await service.create_delivery_note(
            customer_id=sample_customer.id,
            items=[{"batch_id": sample_batch.id, "quantity": Decimal("20")}],
            user_id=sample_user.id,
            notes="הערות למסמך PDF",
        )
        await db_session.flush()
        
        pdf_bytes = await service.generate_delivery_note_pdf(dn.id)
        
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        # PDF files start with %PDF
        assert pdf_bytes[:4] == b'%PDF'


class TestDeliveryNotesAPI:
    """Test delivery notes API endpoints"""
    
    @pytest.fixture
    async def auth_token(self, client, db_session):
        """Get auth token for warehouse user"""
        from app.models.user import UserRole
        
        user = User(
            username="dn_warehouse_user",
            email="dn_warehouse@test.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="DN Warehouse User",
            role=UserRole.WAREHOUSE_WORKER,
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        
        response = await client.post("/api/v1/auth/login", json={
            "username": "dn_warehouse_user",
            "password": "testpass123",
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    async def sample_data(self, db_session):
        """Create sample data for API tests"""
        customer = Customer(
            name="API Test Customer",
            address="123 Test St",
        )
        db_session.add(customer)
        
        item = Item(
            sku="API-INK-001",
            name="API Test Ink",
            supplier="Test Supplier",
            unit_of_measure="kg",
            cost_price=Decimal("50.00"),
        )
        db_session.add(item)
        await db_session.flush()
        
        batch = Batch(
            batch_number="API-BT-001",
            item_id=item.id,
            expiration_date=date.today() + timedelta(days=90),
            receipt_date=date.today(),
            quantity_received=Decimal("200.00"),
            quantity_available=Decimal("200.00"),
            status=BatchStatus.ACTIVE,
        )
        db_session.add(batch)
        await db_session.flush()
        
        return {"customer": customer, "item": item, "batch": batch}
    
    async def test_list_delivery_notes_empty(self, client, auth_token):
        """Test listing delivery notes when empty"""
        response = await client.get(
            "/api/v1/delivery-notes",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
    
    async def test_create_delivery_note_api(self, client, auth_token, sample_data):
        """Test creating delivery note via API"""
        response = await client.post(
            "/api/v1/delivery-notes",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "customer_id": str(sample_data["customer"].id),
                "items": [
                    {
                        "batch_id": str(sample_data["batch"].id),
                        "quantity": 30.0,
                    }
                ],
                "notes": "API test note",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "delivery_note_number" in data
        assert data["items_count"] == 1
    
    async def test_get_delivery_note_details_api(self, client, auth_token, sample_data, db_session):
        """Test getting delivery note details via API"""
        # First create a DN
        service = DocumentService(db_session)
        user_result = await db_session.execute(
            select(User).where(User.email == "dn_warehouse@test.com")
        )
        user = user_result.scalar_one()
        
        dn = await service.create_delivery_note(
            customer_id=sample_data["customer"].id,
            items=[{"batch_id": sample_data["batch"].id, "quantity": Decimal("25")}],
            user_id=user.id,
        )
        await db_session.commit()
        
        response = await client.get(
            f"/api/v1/delivery-notes/{dn.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["delivery_note_number"] == dn.delivery_note_number
        assert len(data["items"]) == 1
    
    async def test_download_delivery_note_pdf_api(self, client, auth_token, sample_data, db_session):
        """Test downloading delivery note PDF via API"""
        # Create a DN
        service = DocumentService(db_session)
        user_result = await db_session.execute(
            select(User).where(User.email == "dn_warehouse@test.com")
        )
        user = user_result.scalar_one()
        
        dn = await service.create_delivery_note(
            customer_id=sample_data["customer"].id,
            items=[{"batch_id": sample_data["batch"].id, "quantity": Decimal("10")}],
            user_id=user.id,
        )
        await db_session.commit()
        
        response = await client.get(
            f"/api/v1/delivery-notes/{dn.id}/pdf",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:4] == b'%PDF'
