"""Tests for goods receipt functionality"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.location import Location
from app.models.user import User


@pytest.fixture
async def test_item(db_session: AsyncSession) -> Item:
    """Create a test item"""
    item = Item(
        id=uuid4(),
        sku="INK-TEST-001",
        name="Test Black Ink",
        supplier="Test Supplier",
        unit_of_measure="KG",
        cost_price=Decimal("50.00"),
        reorder_point=10,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest.fixture
async def test_location(db_session: AsyncSession) -> Location:
    """Create a test location"""
    location = Location(
        id=uuid4(),
        warehouse="WH1",
        shelf="A",
        position="01",
        location_code="WH1-A-01",
        is_active=True,
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest.mark.asyncio
async def test_receive_single_item(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    test_location: Location,
):
    """Test receiving a single item"""
    expiration_date = date.today() + timedelta(days=365)
    
    response = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "100.5",
            "expiration_date": expiration_date.isoformat(),
            "location_id": str(test_location.id),
            "notes": "Test receipt",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "grn_number" in data
    assert data["grn_number"].startswith("GRN-")
    assert "batch_number" in data
    assert data["batch_number"].startswith("GR-")
    assert float(data["quantity"]) == 100.5


@pytest.mark.asyncio
async def test_receive_with_custom_batch_number(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """Test receiving with a custom batch number"""
    expiration_date = date.today() + timedelta(days=180)
    
    response = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "50",
            "expiration_date": expiration_date.isoformat(),
            "batch_number": "CUSTOM-BATCH-001",
            "supplier_batch_number": "SUP-2024-001",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["batch_number"] == "CUSTOM-BATCH-001"


@pytest.mark.asyncio
async def test_receive_expired_date_rejected(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """Test that receiving with expired date is rejected"""
    expired_date = date.today() - timedelta(days=1)
    
    response = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "50",
            "expiration_date": expired_date.isoformat(),
        },
    )
    
    assert response.status_code == 400
    assert "תפוגה" in response.json()["detail"]  # Contains "expiration" in Hebrew


@pytest.mark.asyncio
async def test_receive_nonexistent_item_rejected(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test that receiving for non-existent item is rejected"""
    response = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(uuid4()),
            "quantity": "50",
            "expiration_date": (date.today() + timedelta(days=180)).isoformat(),
        },
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_receive_multiple_items(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    db_session: AsyncSession,
):
    """Test receiving multiple items in a single GRN"""
    # Create another item
    item2 = Item(
        id=uuid4(),
        sku="INK-TEST-002",
        name="Test Cyan Ink",
        supplier="Test Supplier",
        unit_of_measure="KG",
    )
    db_session.add(item2)
    await db_session.commit()
    
    expiration_date = date.today() + timedelta(days=365)
    
    response = await client.post(
        "/api/v1/receiving/receive-multiple",
        headers=auth_headers,
        json={
            "items": [
                {
                    "item_id": str(test_item.id),
                    "quantity": "100",
                    "expiration_date": expiration_date.isoformat(),
                },
                {
                    "item_id": str(item2.id),
                    "quantity": "75",
                    "expiration_date": expiration_date.isoformat(),
                },
            ]
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["batches_created"] == 2
    assert float(data["total_quantity"]) == 175
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_receive_with_expiration_warning(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """Test that receiving with near expiration triggers warning"""
    near_expiration = date.today() + timedelta(days=45)
    
    response = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "50",
            "expiration_date": near_expiration.isoformat(),
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["warning"] is not None
    assert data["warning"]["level"] in ["warning", "critical"]


@pytest.mark.asyncio
async def test_validate_barcode(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """Test barcode validation endpoint"""
    response = await client.post(
        "/api/v1/receiving/validate-barcode",
        headers=auth_headers,
        params={"sku": test_item.sku},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["sku"] == test_item.sku
    assert data["name"] == test_item.name


@pytest.mark.asyncio
async def test_validate_barcode_not_found(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test barcode validation for non-existent SKU"""
    response = await client.post(
        "/api/v1/receiving/validate-barcode",
        headers=auth_headers,
        params={"sku": "NON-EXISTENT-SKU"},
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_batch_number(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test batch number generation"""
    response = await client.get(
        "/api/v1/receiving/generate-batch-number",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "batch_number" in data
    assert data["batch_number"].startswith("GR-")

