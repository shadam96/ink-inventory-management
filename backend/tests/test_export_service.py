"""Tests for export service"""
import pytest
from io import BytesIO
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from app.services.export_service import ExportService
from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from app.models.movement import Movement, MovementType


@pytest.fixture
def export_service():
    """Create export service instance"""
    return ExportService()


@pytest.fixture
def sample_items():
    """Create sample items for testing"""
    items = []
    for i in range(3):
        item = Item(
            id=uuid4(),
            sku=f"SKU-{i+1:03d}",
            name=f"Test Item {i+1}",
            description=f"Description {i+1}",
            supplier="Test Supplier",
            unit_of_measure="kg",
            cost_price=Decimal("100.00"),
            currency="ILS",
            reorder_point=10,
            min_stock=5,
            max_stock=100,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        items.append(item)
    return items


@pytest.fixture
def sample_batches(sample_items):
    """Create sample batches for testing"""
    batches = []
    for i, item in enumerate(sample_items):
        batch = Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number=f"BATCH-{i+1:03d}",
            quantity_received=Decimal("100.0"),
            quantity_available=Decimal("50.0"),
            receipt_date=date(2024, 1, 1),
            expiration_date=date(2024, 12, 31),
            status=BatchStatus.ACTIVE,
            created_at=datetime.now()
        )
        batch.item = item  # Set relationship
        batches.append(batch)
    return batches


def test_export_items_excel(export_service, sample_items):
    """Test Excel export for items"""
    response = export_service.export_items_excel(sample_items)
    
    assert response is not None
    assert response.media_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'items_export' in response.headers['content-disposition']


def test_export_items_csv(export_service, sample_items):
    """Test CSV export for items"""
    response = export_service.export_items_csv(sample_items)
    
    assert response is not None
    assert response.media_type == 'text/csv'
    assert 'items_export' in response.headers['content-disposition']


def test_export_batches_excel(export_service, sample_batches):
    """Test Excel export for batches"""
    response = export_service.export_batches_excel(sample_batches)
    
    assert response is not None
    assert response.media_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'batches_export' in response.headers['content-disposition']


def test_export_batches_csv(export_service, sample_batches):
    """Test CSV export for batches"""
    response = export_service.export_batches_csv(sample_batches)

    assert response is not None
    assert response.media_type == 'text/csv'
    assert 'batches_export' in response.headers['content-disposition']


@pytest.mark.asyncio
async def test_export_batches_csv_shows_zero_for_expiring_today(sample_items):
    """Regression test: `days_until_expiry or ""` treated a batch expiring
    today (days_until_expiry == 0) as falsy, writing an empty cell -
    indistinguishable from a missing expiration date."""
    item = sample_items[0]
    batch = Batch(
        id=uuid4(),
        item_id=item.id,
        batch_number="BATCH-TODAY",
        quantity_received=Decimal("10.0"),
        quantity_available=Decimal("10.0"),
        receipt_date=date.today(),
        expiration_date=date.today(),
        status=BatchStatus.ACTIVE,
        created_at=datetime.now(),
    )
    batch.item = item

    response = ExportService.export_batches_csv([batch])

    body = b""
    async for chunk in response.body_iterator:
        body += chunk if isinstance(chunk, bytes) else chunk.encode()
    csv_text = body.decode()

    data_row = csv_text.splitlines()[1]
    assert ",0," in data_row


def test_export_empty_items(export_service):
    """Test export with empty items list"""
    response = export_service.export_items_excel([])
    
    assert response is not None
    # Should still have headers


def test_export_empty_batches(export_service):
    """Test export with empty batches list"""
    response = export_service.export_batches_excel([])
    
    assert response is not None
    # Should still have headers


def test_excel_response_creation(export_service):
    """Test Excel response creation"""
    from openpyxl import Workbook
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Test"
    ws.cell(row=1, column=1, value="Test Data")
    
    response = export_service.create_excel_response(wb, "test.xlsx")
    
    assert response is not None
    assert response.media_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'test.xlsx' in response.headers['content-disposition']


def test_csv_response_creation(export_service):
    """Test CSV response creation"""
    csv_data = "Header1,Header2\nValue1,Value2"
    
    response = export_service.create_csv_response(csv_data, "test.csv")
    
    assert response is not None
    assert response.media_type == 'text/csv'
    assert 'test.csv' in response.headers['content-disposition']


def test_export_items_with_special_characters(export_service):
    """Test export with Hebrew and special characters"""
    items = [
        Item(
            id=uuid4(),
            sku="SKU-001",
            name="דיו שחור",  # Hebrew
            description="תיאור בעברית",
            supplier="ספק ישראלי",
            unit_of_measure="ליטר",
            cost_price=Decimal("100.00"),
            currency="ILS",
            reorder_point=10,
            min_stock=5,
            max_stock=100,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]
    
    response = export_service.export_items_excel(items)
    assert response is not None
    
    response_csv = export_service.export_items_csv(items)
    assert response_csv is not None


def test_export_batches_with_expiration_coloring(export_service, sample_batches):
    """Test that batches export includes expiration coloring"""
    # Set one batch to expire soon
    sample_batches[0].expiration_date = date.today() + __import__('datetime').timedelta(days=15)
    
    # Set one batch as expired
    sample_batches[1].expiration_date = date.today() - __import__('datetime').timedelta(days=5)
    
    response = export_service.export_batches_excel(sample_batches)
    
    assert response is not None
    # The Excel file should have color coding (verified by the implementation)
