"""Tests for the shared pending-receipt queue and short-expiry alert flow"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.batch import Batch
from app.models.item import Item
from app.models.location import Location
from app.models.pending_receipt import PendingReceiptItem


@pytest.fixture
async def test_item(db_session: AsyncSession) -> Item:
    item = Item(
        id=uuid4(),
        sku="INK-PEND-001",
        name="Pending Black Ink",
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
async def second_item(db_session: AsyncSession) -> Item:
    item = Item(
        id=uuid4(),
        sku="INK-PEND-002",
        name="Pending Cyan Ink",
        supplier="Test Supplier",
        unit_of_measure="KG",
        cost_price=Decimal("75.00"),
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_pending_list_starts_empty(
    client: AsyncClient,
    auth_headers: dict,
):
    response = await client.get("/api/v1/receiving/pending", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_add_pending_returns_adder_metadata(
    client: AsyncClient,
    auth_headers: dict,
    test_user,
    test_item: Item,
):
    expiration = (date.today() + timedelta(days=365)).isoformat()
    response = await client.post(
        "/api/v1/receiving/pending",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "5",
            "expiration_date": expiration,
            "supplier_batch_number": "SUP-ACME-99",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["item_sku"] == test_item.sku
    assert data["item_name"] == test_item.name
    assert data["added_by_username"] == test_user.username
    assert data["supplier_batch_number"] == "SUP-ACME-99"
    assert data["added_by_user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_pending_list_shows_added_rows_sorted_by_time(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    second_item: Item,
):
    exp = (date.today() + timedelta(days=200)).isoformat()
    for item in (test_item, second_item):
        r = await client.post(
            "/api/v1/receiving/pending",
            headers=auth_headers,
            json={
                "item_id": str(item.id),
                "quantity": "3",
                "expiration_date": exp,
            },
        )
        assert r.status_code == 200

    listing = await client.get("/api/v1/receiving/pending", headers=auth_headers)
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 2
    assert rows[0]["item_id"] == str(test_item.id)
    assert rows[1]["item_id"] == str(second_item.id)


@pytest.mark.asyncio
async def test_add_pending_rejects_past_expiration(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    response = await client.post(
        "/api/v1/receiving/pending",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "5",
            "expiration_date": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_remove_pending(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    exp = (date.today() + timedelta(days=100)).isoformat()
    add = await client.post(
        "/api/v1/receiving/pending",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "1",
            "expiration_date": exp,
        },
    )
    pending_id = add.json()["id"]

    r = await client.delete(
        f"/api/v1/receiving/pending/{pending_id}",
        headers=auth_headers,
    )
    assert r.status_code == 200

    listing = (await client.get("/api/v1/receiving/pending", headers=auth_headers)).json()
    assert listing == []


@pytest.mark.asyncio
async def test_remove_pending_unknown_id_404s(
    client: AsyncClient,
    auth_headers: dict,
):
    r = await client.delete(
        f"/api/v1/receiving/pending/{uuid4()}",
        headers=auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_receive_all_drains_queue_and_creates_batches(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_item: Item,
    second_item: Item,
):
    exp = (date.today() + timedelta(days=400)).isoformat()
    for item, qty in ((test_item, "10"), (second_item, "7")):
        r = await client.post(
            "/api/v1/receiving/pending",
            headers=auth_headers,
            json={
                "item_id": str(item.id),
                "quantity": qty,
                "expiration_date": exp,
                "manufacturing_date": (date.today() - timedelta(days=30)).isoformat(),
            },
        )
        assert r.status_code == 200

    drain = await client.post(
        "/api/v1/receiving/pending/receive-all",
        headers=auth_headers,
    )
    assert drain.status_code == 200, drain.text
    body = drain.json()
    assert body["batches_created"] == 2
    assert float(body["total_quantity"]) == 17
    assert body["grn_number"].startswith("GRN-")

    listing = (await client.get("/api/v1/receiving/pending", headers=auth_headers)).json()
    assert listing == []

    # Multi-item path used to drop manufacturing_date; verify it's persisted now.
    batches = (await db_session.execute(select(Batch))).scalars().all()
    assert len(batches) == 2
    for b in batches:
        assert b.manufacturing_date is not None


@pytest.mark.asyncio
async def test_receive_all_empty_queue_400s(
    client: AsyncClient,
    auth_headers: dict,
):
    r = await client.post(
        "/api/v1/receiving/pending/receive-all",
        headers=auth_headers,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_short_expiry_receipt_persists_alert(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_item: Item,
):
    """Option B: critical-window receipt must leave an Alert row behind."""
    r = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "5",
            "expiration_date": (date.today() + timedelta(days=10)).isoformat(),
        },
    )
    assert r.status_code == 200
    warning = r.json()["warning"]
    assert warning is not None
    assert warning["level"] == "critical"

    alerts = (
        await db_session.execute(
            select(Alert).where(Alert.alert_type == AlertType.EXPIRATION_CRITICAL)
        )
    ).scalars().all()
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.CRITICAL


@pytest.mark.asyncio
async def test_info_window_receipt_does_not_persist_alert(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_item: Item,
):
    """150 days out is an info-level warning — surfaced to the UI but not
    added to the alert center, to keep it from getting noisy."""
    r = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "5",
            "expiration_date": (date.today() + timedelta(days=150)).isoformat(),
        },
    )
    assert r.status_code == 200
    assert r.json()["warning"]["level"] == "info"

    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert alerts == []


@pytest.mark.asyncio
async def test_receive_multiple_persists_manufacturing_date(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_item: Item,
    second_item: Item,
):
    """Regression for the bug where multi-item receipts dropped manufacturing_date."""
    mfg = (date.today() - timedelta(days=15)).isoformat()
    exp = (date.today() + timedelta(days=365)).isoformat()

    r = await client.post(
        "/api/v1/receiving/receive-multiple",
        headers=auth_headers,
        json={
            "items": [
                {
                    "item_id": str(test_item.id),
                    "quantity": "4",
                    "expiration_date": exp,
                    "manufacturing_date": mfg,
                },
                {
                    "item_id": str(second_item.id),
                    "quantity": "6",
                    "expiration_date": exp,
                    "manufacturing_date": mfg,
                },
            ]
        },
    )
    assert r.status_code == 200

    batches = (await db_session.execute(select(Batch))).scalars().all()
    assert len(batches) == 2
    for b in batches:
        assert b.manufacturing_date is not None
        assert b.manufacturing_date.isoformat() == mfg
