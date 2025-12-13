"""Tests for movement history and audit trail"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.movement import Movement, MovementType
from app.models.user import User


@pytest.fixture
async def item_with_movements(
    db_session: AsyncSession,
    test_user: User,
) -> tuple[Item, Batch, list[Movement]]:
    """Create an item with batch and movements"""
    item = Item(
        id=uuid4(),
        sku="MOV-TEST-001",
        name="Movement Test Ink",
        supplier="Test Supplier",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.flush()
    
    batch = Batch(
        id=uuid4(),
        item_id=item.id,
        batch_number="MOV-BATCH-001",
        quantity_received=Decimal("100"),
        quantity_available=Decimal("70"),
        receipt_date=date.today() - timedelta(days=10),
        expiration_date=date.today() + timedelta(days=180),
        status=BatchStatus.ACTIVE,
    )
    db_session.add(batch)
    await db_session.flush()
    
    movements = [
        Movement(
            id=uuid4(),
            batch_id=batch.id,
            user_id=test_user.id,
            movement_type=MovementType.RECEIPT,
            quantity=Decimal("100"),
            quantity_before=Decimal("0"),
            quantity_after=Decimal("100"),
            reference_number="GRN-001",
            notes="Initial receipt",
        ),
        Movement(
            id=uuid4(),
            batch_id=batch.id,
            user_id=test_user.id,
            movement_type=MovementType.DISPATCH,
            quantity=Decimal("30"),
            quantity_before=Decimal("100"),
            quantity_after=Decimal("70"),
            reference_number="DSP-001",
            notes="First dispatch",
        ),
    ]
    
    for movement in movements:
        db_session.add(movement)
    
    await db_session.commit()
    return item, batch, movements


@pytest.mark.asyncio
async def test_get_movement_history(
    client: AsyncClient,
    auth_headers: dict,
    item_with_movements: tuple[Item, Batch, list[Movement]],
):
    """Test getting movement history"""
    item, batch, movements = item_with_movements
    
    response = await client.get(
        "/api/v1/movements",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_movements_by_batch(
    client: AsyncClient,
    auth_headers: dict,
    item_with_movements: tuple[Item, Batch, list[Movement]],
):
    """Test getting movements for a specific batch"""
    item, batch, movements = item_with_movements
    
    response = await client.get(
        f"/api/v1/movements/by-batch/{batch.id}",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["batch_id"] == str(batch.id)


@pytest.mark.asyncio
async def test_get_movements_by_item(
    client: AsyncClient,
    auth_headers: dict,
    item_with_movements: tuple[Item, Batch, list[Movement]],
):
    """Test getting movements for a specific item"""
    item, batch, movements = item_with_movements
    
    response = await client.get(
        f"/api/v1/movements/by-item/{item.id}",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert "summary" in data
    assert float(data["summary"]["total_received"]) == 100
    assert float(data["summary"]["total_dispatched"]) == 30


@pytest.mark.asyncio
async def test_filter_movements_by_type(
    client: AsyncClient,
    auth_headers: dict,
    item_with_movements: tuple[Item, Batch, list[Movement]],
):
    """Test filtering movements by type"""
    response = await client.get(
        "/api/v1/movements",
        headers=auth_headers,
        params={"movement_type": "dispatch"},
    )
    
    assert response.status_code == 200
    data = response.json()
    # All returned movements should be dispatches
    for m in data["movements"]:
        assert m["movement_type"] == "dispatch"


@pytest.mark.asyncio
async def test_movements_include_audit_info(
    client: AsyncClient,
    auth_headers: dict,
    item_with_movements: tuple[Item, Batch, list[Movement]],
):
    """Test that movements include full audit trail info"""
    item, batch, movements = item_with_movements
    
    response = await client.get(
        f"/api/v1/movements/by-batch/{batch.id}",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    for movement in data["movements"]:
        assert "quantity_before" in movement
        assert "quantity_after" in movement
        assert "timestamp" in movement
        assert "user_name" in movement
        assert "reference_number" in movement

