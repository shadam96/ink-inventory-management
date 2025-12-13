"""Tests for picking and dispatch functionality"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.user import User


@pytest.fixture
async def item_with_stock(db_session: AsyncSession) -> tuple[Item, list[Batch]]:
    """Create an item with stock in multiple batches"""
    item = Item(
        id=uuid4(),
        sku="PICK-TEST-001",
        name="Pick Test Ink",
        supplier="Test Supplier",
        unit_of_measure="KG",
        cost_price=Decimal("50.00"),
    )
    db_session.add(item)
    await db_session.flush()
    
    today = date.today()
    
    batches = [
        Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number="PICK-001",
            quantity_received=Decimal("100"),
            quantity_available=Decimal("100"),
            receipt_date=today - timedelta(days=30),
            expiration_date=today + timedelta(days=60),
            status=BatchStatus.ACTIVE,
        ),
        Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number="PICK-002",
            quantity_received=Decimal("150"),
            quantity_available=Decimal("150"),
            receipt_date=today - timedelta(days=20),
            expiration_date=today + timedelta(days=120),
            status=BatchStatus.ACTIVE,
        ),
    ]
    
    for batch in batches:
        db_session.add(batch)
    
    await db_session.commit()
    return item, batches


@pytest.mark.asyncio
async def test_suggest_batches(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """Test batch suggestion endpoint"""
    item, batches = item_with_stock
    
    response = await client.post(
        "/api/v1/picking/suggest-batches",
        headers=auth_headers,
        json={
            "item_id": str(item.id),
            "quantity_needed": "50",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["can_fulfill"] is True
    assert len(data["suggestions"]) == 1
    assert data["suggestions"][0]["batch_number"] == "PICK-001"  # Earliest expiring


@pytest.mark.asyncio
async def test_suggest_batches_insufficient_stock(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """Test batch suggestion with insufficient stock"""
    item, batches = item_with_stock
    
    response = await client.post(
        "/api/v1/picking/suggest-batches",
        headers=auth_headers,
        json={
            "item_id": str(item.id),
            "quantity_needed": "500",  # More than available (250)
        },
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_validate_pick(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """Test pick validation endpoint"""
    item, batches = item_with_stock
    
    response = await client.post(
        "/api/v1/picking/validate-pick",
        headers=auth_headers,
        json={
            "batch_id": str(batches[0].id),
            "quantity": "50",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True


@pytest.mark.asyncio
async def test_execute_pick(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """Test executing a pick"""
    item, batches = item_with_stock
    
    response = await client.post(
        "/api/v1/picking/execute-pick",
        headers=auth_headers,
        json={
            "batch_id": str(batches[0].id),
            "quantity": "30",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert float(data["quantity"]) == 30
    assert float(data["quantity_remaining"]) == 70  # 100 - 30


@pytest.mark.asyncio
async def test_execute_pick_insufficient_quantity(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """Test that picking more than available is rejected"""
    item, batches = item_with_stock
    
    response = await client.post(
        "/api/v1/picking/execute-pick",
        headers=auth_headers,
        json={
            "batch_id": str(batches[0].id),
            "quantity": "150",  # More than 100 available
        },
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_dispatch(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """Test creating a dispatch with multiple items"""
    item, batches = item_with_stock
    
    response = await client.post(
        "/api/v1/picking/dispatch",
        headers=auth_headers,
        json={
            "items": [
                {
                    "batch_id": str(batches[0].id),
                    "quantity": "50",
                },
                {
                    "batch_id": str(batches[1].id),
                    "quantity": "75",
                },
            ],
            "notes": "Test dispatch",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["items_dispatched"] == 2
    assert float(data["total_quantity"]) == 125
    assert data["reference_number"].startswith("DSP-")


@pytest.mark.asyncio
async def test_dispatch_atomic_rollback(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """Test that dispatch is atomic - all or nothing"""
    item, batches = item_with_stock
    
    # Second item has invalid quantity
    response = await client.post(
        "/api/v1/picking/dispatch",
        headers=auth_headers,
        json={
            "items": [
                {
                    "batch_id": str(batches[0].id),
                    "quantity": "50",
                },
                {
                    "batch_id": str(batches[1].id),
                    "quantity": "200",  # More than available (150)
                },
            ],
        },
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_expiration_summary(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """Test expiration summary endpoint"""
    item, batches = item_with_stock
    
    response = await client.get(
        f"/api/v1/picking/expiration-summary/{item.id}",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert float(data["total_quantity"]) == 250  # 100 + 150
    assert data["total_batches"] == 2
    assert "breakdown" in data

