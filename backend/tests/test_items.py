"""Tests for inventory/item endpoints"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

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


def _uuid(n: int) -> UUID:
    """Deterministic, sortable id. The letters matter: SQLite gives the
    UUID column NUMERIC affinity, so an all-digit hex id is read back as an
    int."""
    return UUID(f"aaaaaaaa-0000-0000-0000-{n:012d}")


async def _fetch_all_pages(client: AsyncClient, headers: dict, **params) -> list:
    rows, page = [], 1
    while True:
        response = await client.get(
            "/api/v1/items", headers=headers, params={**params, "page": page, "page_size": 2}
        )
        assert response.status_code == 200
        data = response.json()
        rows.extend(data["items"])
        if page >= data["pages"]:
            return rows
        page += 1


@pytest.mark.asyncio
async def test_list_items_default_order_is_name_then_id(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Regression test: with no sort_by the query had no ORDER BY, so
    Postgres could return OFFSET/LIMIT pages in any order - the item
    dropdowns, which page through the catalog, could show a different
    subset (or skip/repeat items) on every fetch. Inserted out of order,
    with a name tie, to prove the ordering comes from the query."""
    rows = [
        (_uuid(5), "Magenta Ink"),
        (_uuid(4), "Cyan Ink"),
        (_uuid(3), "Yellow Ink"),
        (_uuid(2), "Black Ink"),
        (_uuid(1), "Black Ink"),
    ]
    for item_id, name in rows:
        db_session.add(Item(
            id=item_id, sku=f"INK-ORD-{item_id.int}", name=name,
            supplier="Supplier A", unit_of_measure="KG",
        ))
        # One INSERT per row: SQLAlchemy's batched insert trips over
        # explicit UUID primary keys on SQLite.
        await db_session.flush()
    await db_session.commit()

    listed = await _fetch_all_pages(client, auth_headers)

    assert [(r["id"], r["name"]) for r in listed] == [
        (str(item_id), name) for item_id, name in sorted(rows, key=lambda r: (r[1], r[0]))
    ]


@pytest.mark.asyncio
async def test_list_items_below_reorder_filters_before_paginating(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """Regression test: below_reorder was applied in Python to the page
    already cut by OFFSET/LIMIT, so pages came back short or empty and
    total/pages still counted every item. Stock is pickable stock only -
    an expired batch doesn't keep an item off the reorder list."""
    stock = {
        "A Stocked": (Decimal("50"), 30),      # 50 >= 10
        "B Low": (Decimal("5"), 0),            # 5 < 10
        "C Expired Only": (Decimal("50"), -1),  # expired stock doesn't count
        "D Empty": (None, None),               # no batches at all
    }
    for name, (qty, expires_in) in stock.items():
        item = Item(
            sku=f"INK-RO-{name[0]}", name=name, supplier="Supplier A",
            unit_of_measure="KG", reorder_point=10,
        )
        db_session.add(item)
        await db_session.flush()
        if qty is not None:
            db_session.add(Batch(
                batch_number=f"BT-RO-{name[0]}", item_id=item.id,
                expiration_date=date.today() + timedelta(days=expires_in),
                receipt_date=date.today() - timedelta(days=60),
                quantity_received=qty, quantity_available=qty,
                status=BatchStatus.ACTIVE,
            ))
    await db_session.commit()

    response = await client.get(
        "/api/v1/items", headers=auth_headers,
        params={"below_reorder": True, "page_size": 1},
    )
    data = response.json()
    assert data["total"] == 3
    assert data["pages"] == 3
    assert [i["name"] for i in data["items"]] == ["B Low"]

    below = await _fetch_all_pages(client, auth_headers, below_reorder=True)
    assert [i["name"] for i in below] == ["B Low", "C Expired Only", "D Empty"]
    above = await _fetch_all_pages(client, auth_headers, below_reorder=False)
    assert [i["name"] for i in above] == ["A Stocked"]


@pytest.mark.asyncio
async def test_list_items_sort_by_breaks_ties_by_id(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """An explicit sort_by on a non-unique column needs the same id
    tiebreaker, or equal values can swap places between pages."""
    for i in (4, 3, 2, 1):
        db_session.add(Item(
            id=_uuid(i), sku=f"INK-TIE-{i}", name=f"Ink {i}",
            supplier="Same Supplier", unit_of_measure="KG",
        ))
        await db_session.flush()
    await db_session.commit()

    listed = await _fetch_all_pages(client, auth_headers, sort_by="supplier")

    assert [r["id"] for r in listed] == [str(_uuid(i)) for i in (1, 2, 3, 4)]


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


