"""Tests for export API endpoints"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal
from datetime import date

from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_export_items_excel_unauthorized(client: AsyncClient):
    """Test exporting items without auth"""
    response = await client.get("/api/v1/items/export/excel")
    assert response.status_code in [401, 403]  # Either unauthorized or forbidden


@pytest.mark.asyncio
async def test_export_items_excel_success(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession
):
    """Test successful Excel export of items"""
    # Create test items
    for i in range(3):
        item = Item(
            id=uuid4(),
            sku=f"SKU-{i:03d}",
            name=f"Test Item {i}",
            supplier="Test Supplier",
            unit_of_measure="kg",
            cost_price=Decimal("100.00"),
            currency="ILS",
            reorder_point=10,
            min_stock=5,
            max_stock=100
        )
        db_session.add(item)
    await db_session.commit()
    
    response = await client.get(
        "/api/v1/items/export/excel",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'items_export' in response.headers['content-disposition']
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_export_items_csv_success(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession
):
    """Test successful CSV export of items"""
    # Create test item
    item = Item(
        id=uuid4(),
        sku="SKU-001",
        name="Test Item",
        supplier="Test Supplier",
        unit_of_measure="kg",
        cost_price=Decimal("100.00"),
        currency="ILS",
        reorder_point=10,
        min_stock=5,
        max_stock=100
    )
    db_session.add(item)
    await db_session.commit()
    
    response = await client.get(
        "/api/v1/items/export/csv",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/csv; charset=utf-8'
    assert 'items_export' in response.headers['content-disposition']


@pytest.mark.asyncio
async def test_export_batches_excel_success(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession
):
    """Test successful Excel export of batches"""
    # Create test item and batch
    item = Item(
        id=uuid4(),
        sku="SKU-001",
        name="Test Item",
        supplier="Test Supplier",
        unit_of_measure="kg",
        cost_price=Decimal("100.00"),
        currency="ILS",
        reorder_point=10,
        min_stock=5,
        max_stock=100
    )
    db_session.add(item)
    await db_session.flush()
    
    batch = Batch(
        id=uuid4(),
        item_id=item.id,
        batch_number="BATCH-001",
        quantity_received=Decimal("100.0"),
        quantity_available=Decimal("50.0"),
        receipt_date=date(2024, 1, 1),
        expiration_date=date(2024, 12, 31),
        status=BatchStatus.ACTIVE
    )
    db_session.add(batch)
    await db_session.commit()
    
    response = await client.get(
        "/api/v1/batches/export/excel",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert 'batches_export' in response.headers['content-disposition']


@pytest.mark.asyncio
async def test_export_batches_csv_success(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession
):
    """Test successful CSV export of batches"""
    # Create test item and batch
    item = Item(
        id=uuid4(),
        sku="SKU-001",
        name="Test Item",
        supplier="Test Supplier",
        unit_of_measure="kg",
        cost_price=Decimal("100.00"),
        currency="ILS",
        reorder_point=10,
        min_stock=5,
        max_stock=100
    )
    db_session.add(item)
    await db_session.flush()
    
    batch = Batch(
        id=uuid4(),
        item_id=item.id,
        batch_number="BATCH-001",
        quantity_received=Decimal("100.0"),
        quantity_available=Decimal("50.0"),
        receipt_date=date(2024, 1, 1),
        expiration_date=date(2024, 12, 31),
        status=BatchStatus.ACTIVE
    )
    db_session.add(batch)
    await db_session.commit()
    
    response = await client.get(
        "/api/v1/batches/export/csv",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert 'batches_export' in response.headers['content-disposition']


@pytest.mark.asyncio
async def test_export_movements_excel_success(
    client: AsyncClient,
    auth_headers: dict
):
    """Test successful Excel export of movements"""
    response = await client.get(
        "/api/v1/movements/export/excel",
        headers=auth_headers
    )
    
    # Should work even with no movements
    assert response.status_code == 200
    assert 'movements_export' in response.headers['content-disposition']


@pytest.mark.asyncio
async def test_export_movements_csv_success(
    client: AsyncClient,
    auth_headers: dict
):
    """Test successful CSV export of movements"""
    response = await client.get(
        "/api/v1/movements/export/csv",
        headers=auth_headers
    )
    
    # Should work even with no movements
    assert response.status_code == 200
    assert 'movements_export' in response.headers['content-disposition']


@pytest.mark.asyncio
async def test_export_empty_data(
    client: AsyncClient,
    auth_headers: dict
):
    """Test exporting with no data"""
    response = await client.get(
        "/api/v1/items/export/excel",
        headers=auth_headers
    )
    
    # Should still return valid file with headers
    assert response.status_code == 200
    assert len(response.content) > 0
