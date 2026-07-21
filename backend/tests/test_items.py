"""Tests for inventory/item endpoints"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.user import User


@pytest.mark.asyncio
async def test_create_item(client: AsyncClient, auth_headers: dict):
    """Test creating a new item"""
    response = await client.post(
        "/api/v1/items",
        headers=auth_headers,
        json={
            "sku": "INK-001",
            "name": "Black Ink",
            "supplier": "Supplier A",
            "unit_of_measure": "KG",
            "cost_price": "50.00",
            "reorder_point": 10,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "INK-001"
    assert data["name"] == "Black Ink"
    assert data["supplier"] == "Supplier A"
    assert float(data["cost_price"]) == 50.00


@pytest.mark.asyncio
async def test_create_item_rejects_min_stock_above_max_stock(
    client: AsyncClient, auth_headers: dict
):
    """Regression test: min_stock/max_stock/reorder_point were each
    validated independently (ge=0), so min_stock=100, max_stock=5 was
    previously accepted and broke reorder-alert logic (is_below_reorder /
    low-stock checks compare against a max_stock that's nonsensically
    lower than the minimum)."""
    response = await client.post(
        "/api/v1/items",
        headers=auth_headers,
        json={
            "sku": "INK-BADSTOCK-001",
            "name": "Black Ink",
            "supplier": "Supplier A",
            "unit_of_measure": "KG",
            "min_stock": 100,
            "max_stock": 5,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_item_rejects_reorder_point_above_max_stock(
    client: AsyncClient, auth_headers: dict
):
    """Same cross-field gap for reorder_point vs max_stock."""
    response = await client.post(
        "/api/v1/items",
        headers=auth_headers,
        json={
            "sku": "INK-BADREORDER-001",
            "name": "Black Ink",
            "supplier": "Supplier A",
            "unit_of_measure": "KG",
            "reorder_point": 200,
            "max_stock": 100,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_item_rejects_min_stock_above_max_stock(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Same cross-field check applies to partial updates when both fields
    being compared are present in the same request."""
    item = Item(
        sku="INK-UPDATESTOCK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
        min_stock=5,
        max_stock=100,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await client.put(
        f"/api/v1/items/{item.id}",
        headers=auth_headers,
        json={"min_stock": 50, "max_stock": 10},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_duplicate_sku(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Test creating item with duplicate SKU fails"""
    # Create first item
    item = Item(
        sku="INK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.commit()
    
    # Try to create duplicate
    response = await client.post(
        "/api/v1/items",
        headers=auth_headers,
        json={
            "sku": "INK-001",
            "name": "Another Ink",
            "supplier": "Supplier B",
        },
    )
    assert response.status_code == 400
    assert "כבר קיים" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_items(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Test listing items"""
    # Create some items
    for i in range(3):
        item = Item(
            sku=f"INK-{i:03d}",
            name=f"Ink {i}",
            supplier="Supplier A",
            unit_of_measure="KG",
        )
        db_session.add(item)
    await db_session.commit()
    
    response = await client.get("/api/v1/items", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_items_with_search(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Test listing items with search filter"""
    # Create items with different names
    item1 = Item(sku="BLACK-001", name="Black Ink", supplier="A", unit_of_measure="KG")
    item2 = Item(sku="CYAN-001", name="Cyan Ink", supplier="A", unit_of_measure="KG")
    db_session.add_all([item1, item2])
    await db_session.commit()
    
    response = await client.get(
        "/api/v1/items", headers=auth_headers, params={"search": "black"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["sku"] == "BLACK-001"


@pytest.mark.asyncio
async def test_get_item(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Test getting a single item"""
    item = Item(
        sku="INK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    response = await client.get(f"/api/v1/items/{item.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["sku"] == "INK-001"


@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting non-existent item returns 404"""
    from uuid import uuid4
    
    response = await client.get(f"/api/v1/items/{uuid4()}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_item(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Test updating an item"""
    item = Item(
        sku="INK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
        cost_price=50.00,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    response = await client.put(
        f"/api/v1/items/{item.id}",
        headers=auth_headers,
        json={"name": "Premium Black Ink", "cost_price": "75.00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Premium Black Ink"
    assert float(data["cost_price"]) == 75.00


@pytest.mark.asyncio
async def test_delete_item(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Test deleting an item without batches"""
    item = Item(
        sku="INK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    response = await client.delete(f"/api/v1/items/{item.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_item_with_active_batch_blocked(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Deleting an item with an ACTIVE batch is rejected."""
    item = Item(
        sku="INK-ACTIVE-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.flush()

    db_session.add(
        Batch(
            batch_number="BT-ACTIVE-001",
            item_id=item.id,
            expiration_date=date.today() + timedelta(days=90),
            receipt_date=date.today(),
            quantity_received=Decimal("10"),
            quantity_available=Decimal("10"),
            status=BatchStatus.ACTIVE,
        )
    )
    await db_session.commit()

    response = await client.delete(f"/api/v1/items/{item.id}", headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_item_with_depleted_batch_blocked(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Deleting an item is rejected even when its only batch is DEPLETED
    (not active) - a depleted batch still carries historical Movement
    records that must not be silently cascade-deleted. This is the fix:
    previously only ACTIVE batches were checked, so an item with solely
    depleted/expired batches could be deleted, cascading through the ORM
    relationship and destroying that batch's movement history even though
    the DB's ondelete=RESTRICT FK was meant to prevent exactly this."""
    item = Item(
        sku="INK-DEPLETED-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.flush()

    db_session.add(
        Batch(
            batch_number="BT-DEPLETED-001",
            item_id=item.id,
            expiration_date=date.today() + timedelta(days=90),
            receipt_date=date.today(),
            quantity_received=Decimal("10"),
            quantity_available=Decimal("0"),
            status=BatchStatus.DEPLETED,
        )
    )
    await db_session.commit()

    response = await client.delete(f"/api/v1/items/{item.id}", headers=auth_headers)
    assert response.status_code == 400

    # The item and its (depleted) batch must both still exist.
    result = await db_session.execute(select(Item).where(Item.id == item.id))
    assert result.scalar_one_or_none() is not None
    result = await db_session.execute(select(Batch).where(Batch.item_id == item.id))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test that endpoints require authentication"""
    response = await client.get("/api/v1/items")
    assert response.status_code == 403


