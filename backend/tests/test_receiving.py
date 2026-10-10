"""Tests for goods receipt functionality"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.location import Location
from app.models.movement import Movement
from app.models.user import User
from app.services.receiving_service import ReceivingService


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
            "quantity": 100,
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
    assert float(data["quantity"]) == 100


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["/api/v1/receiving/receive", "/api/v1/receiving/receive-multiple"])
async def test_receive_rejects_fractional_quantity(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    endpoint: str,
):
    """Scanned boxes are always whole liters - a fractional quantity is a data-entry error"""
    line = {
        "item_id": str(test_item.id),
        "quantity": 100.5,
        "expiration_date": (date.today() + timedelta(days=365)).isoformat(),
    }
    body = line if endpoint.endswith("/receive") else {"items": [line]}

    response = await client.post(endpoint, headers=auth_headers, json=body)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_same_day_receipts_get_distinct_grn_numbers(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """GRN numbers live on movements, not batches - sequencing them against
    batch numbers gave every same-day receipt GRN-YYMMDD-001."""
    expiration_date = date.today() + timedelta(days=365)

    grns = []
    for _ in range(2):
        response = await client.post(
            "/api/v1/receiving/receive",
            headers=auth_headers,
            json={
                "item_id": str(test_item.id),
                "quantity": 10,
                "expiration_date": expiration_date.isoformat(),
            },
        )
        assert response.status_code == 200
        grns.append(response.json()["grn_number"])

    assert grns[0] != grns[1]


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
async def test_receive_multiple_rejects_non_positive_quantity(
    db_session: AsyncSession,
    test_item: Item,
    test_user: User,
):
    """Defense-in-depth regression test: receive_multiple's service layer
    must reject a non-positive quantity itself, not just rely on the
    Pydantic Field(gt=0) at the HTTP layer - any other/future caller of
    this service method (scripts, other endpoints) needs the same
    protection receive_goods already has."""
    service = ReceivingService(db_session)
    expiration_date = date.today() + timedelta(days=365)

    with pytest.raises(ValueError, match="כמות חייבת להיות חיובית"):
        await service.receive_multiple(
            receipts=[
                {
                    "item_id": test_item.id,
                    "quantity": "0",
                    "expiration_date": expiration_date,
                },
            ],
            user_id=test_user.id,
        )


def _receipt(item: Item, **overrides) -> dict:
    """One receipt line, shaped like what the receiving page sends."""
    return {
        "item_id": str(item.id),
        "quantity": 10,
        "expiration_date": (date.today() + timedelta(days=365)).isoformat(),
        **overrides,
    }


async def _batch_count(db_session: AsyncSession) -> int:
    return (await db_session.execute(select(func.count()).select_from(Batch))).scalar_one()


@pytest.mark.asyncio
async def test_receive_multiple_keeps_manufacturing_date(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    db_session: AsyncSession,
):
    """Regression: /receive-multiple never forwarded manufacturing_date, so
    it was silently dropped whenever 2+ lines were received together (the
    single-line /receive kept it)."""
    manufactured = date.today() - timedelta(days=30)

    response = await client.post(
        "/api/v1/receiving/receive-multiple",
        headers=auth_headers,
        json={"items": [
            _receipt(test_item, batch_number="LOT-A", manufacturing_date=manufactured.isoformat()),
            _receipt(test_item, batch_number="LOT-B"),
        ]},
    )

    assert response.status_code == 200
    batches = {b.batch_number: b for b in (await db_session.execute(select(Batch))).scalars()}
    assert batches["LOT-A"].manufacturing_date == manufactured
    assert batches["LOT-B"].manufacturing_date is None


@pytest.mark.asyncio
async def test_receive_multiple_generates_a_number_for_each_blank_batch_number(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """The form sends "" for a left-empty batch field - blank lines must each
    get their own generated number, never count as duplicates of each other."""
    response = await client.post(
        "/api/v1/receiving/receive-multiple",
        headers=auth_headers,
        json={"items": [
            _receipt(test_item, batch_number="LOT-A"),
            _receipt(test_item, batch_number=""),
            _receipt(test_item, batch_number=""),
        ]},
    )

    assert response.status_code == 200
    numbers = [line["batch_number"] for line in response.json()["items"]]
    assert numbers[0] == "LOT-A"
    assert numbers[1].startswith("GR-") and numbers[2].startswith("GR-")
    assert numbers[1] != numbers[2]


@pytest.fixture
async def other_item(db_session: AsyncSession) -> Item:
    item = Item(
        id=uuid4(),
        sku="INK-TEST-002",
        name="Test Cyan Ink",
        supplier="Test Supplier",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.commit()
    return item


def _batch(item: Item, batch_number: str, receipt_date: date, **overrides) -> Batch:
    """A batch as an earlier receipt left it - same expiry as _receipt()."""
    fields = dict(
        item_id=item.id,
        batch_number=batch_number,
        quantity_received=Decimal("10"),
        quantity_available=Decimal("10"),
        receipt_date=receipt_date,
        expiration_date=date.today() + timedelta(days=365),
        status=BatchStatus.ACTIVE,
    )
    return Batch(**{**fields, **overrides})


async def _batches(db_session: AsyncSession, batch_number: str) -> list[Batch]:
    result = await db_session.execute(
        select(Batch).where(Batch.batch_number == batch_number).order_by(Batch.receipt_date)
    )
    return list(result.scalars())


@pytest.mark.asyncio
async def test_receive_multiple_combines_lines_of_one_batch(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    db_session: AsyncSession,
):
    """Two lines with one batch number (two boxes of the same supplier lot)
    are one batch - they used to hit the unique constraint mid-insert and
    fail the whole receipt with an unexplained 500."""
    response = await client.post(
        "/api/v1/receiving/receive-multiple",
        headers=auth_headers,
        json={"items": [
            _receipt(test_item, batch_number="LOT-A", quantity=10),
            _receipt(test_item, batch_number="LOT-B", quantity=10),
            _receipt(test_item, batch_number="LOT-A", quantity=5),
        ]},
    )

    assert response.status_code == 200
    assert float(response.json()["total_quantity"]) == 25
    assert await _batch_count(db_session) == 2
    [lot_a] = await _batches(db_session, "LOT-A")
    assert (lot_a.quantity_received, lot_a.quantity_available) == (15, 15)
    movements = (await db_session.execute(
        select(Movement).where(Movement.batch_id == lot_a.id).order_by(Movement.quantity_after)
    )).scalars().all()
    assert [(m.quantity_before, m.quantity_after) for m in movements] == [(0, 10), (10, 15)]


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["receive", "receive-multiple"])
async def test_receiving_a_batch_again_the_same_day_tops_it_up(
    endpoint: str,
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    db_session: AsyncSession,
):
    """One batch per lot per day: more boxes of a lot already received today
    add their liters to that batch - it used to be rejected outright."""
    first = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json=_receipt(test_item, batch_number="LOT-A", quantity=10),
    )
    assert first.status_code == 200

    repeat = _receipt(test_item, batch_number="LOT-A", quantity=5)
    body = repeat if endpoint == "receive" else {
        "items": [_receipt(test_item, batch_number="LOT-B"), repeat]
    }
    response = await client.post(
        f"/api/v1/receiving/{endpoint}", headers=auth_headers, json=body
    )

    assert response.status_code == 200
    [lot_a] = await _batches(db_session, "LOT-A")
    assert (lot_a.quantity_received, lot_a.quantity_available) == (15, 15)
    # The response reports this receipt's liters, not the batch's new total.
    lines = [response.json()] if endpoint == "receive" else response.json()["items"]
    assert float(lines[-1]["quantity"]) == 5


@pytest.mark.asyncio
async def test_receiving_a_batch_on_a_later_day_creates_a_separate_batch(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    db_session: AsyncSession,
):
    """A later delivery of the same lot is its own batch, with its own
    receipt date and quantities - not merged into the earlier one."""
    yesterday = date.today() - timedelta(days=1)
    db_session.add(_batch(test_item, "LOT-A", yesterday, quantity_received=Decimal("7"), quantity_available=Decimal("7")))
    await db_session.commit()

    response = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json=_receipt(test_item, batch_number="LOT-A", quantity=10),
    )

    assert response.status_code == 200
    earlier, today = await _batches(db_session, "LOT-A")
    assert (earlier.receipt_date, earlier.quantity_available) == (yesterday, 7)
    assert (today.receipt_date, today.quantity_available) == (date.today(), 10)


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["item", "expiration_date"])
async def test_same_day_batch_with_a_different_item_or_expiry_is_rejected(
    mismatch: str,
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    other_item: Item,
    db_session: AsyncSession,
):
    """A batch is one item with one expiry - a same-day line that disagrees
    is a data-entry mistake, never silently added to that batch."""
    first = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json=_receipt(test_item, batch_number="LOT-A"),
    )
    assert first.status_code == 200

    conflicting = (
        _receipt(other_item, batch_number="LOT-A") if mismatch == "item"
        else _receipt(test_item, batch_number="LOT-A",
                      expiration_date=(date.today() + timedelta(days=400)).isoformat())
    )
    response = await client.post(
        "/api/v1/receiving/receive", headers=auth_headers, json=conflicting
    )

    assert response.status_code == 400
    assert "LOT-A" in response.json()["detail"]
    [lot_a] = await _batches(db_session, "LOT-A")
    assert lot_a.quantity_received == 10


@pytest.mark.asyncio
async def test_topping_up_a_batch_depleted_earlier_today_makes_it_pickable_again(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
    db_session: AsyncSession,
):
    batch = _batch(test_item, "LOT-A", date.today(), quantity_available=Decimal("0"), status=BatchStatus.DEPLETED)
    db_session.add(batch)
    await db_session.commit()

    response = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json=_receipt(test_item, batch_number="LOT-A", quantity=5),
    )

    assert response.status_code == 200
    assert batch.status == BatchStatus.ACTIVE
    assert (batch.quantity_received, batch.quantity_available) == (15, 5)


@pytest.mark.asyncio
async def test_receive_rejected_when_less_than_six_months_shelf_life(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """Receiving must be hard-blocked when less than 180 days (~6 months)
    remain until expiration - this supersedes the old expectation that a
    45-day-out item would be received with just a warning."""
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

    assert response.status_code == 400
    assert "180" in response.json()["detail"]


@pytest.mark.asyncio
async def test_receive_accepted_at_exactly_six_months(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """Exactly 180 days out is the boundary and must still be accepted."""
    expiration_date = date.today() + timedelta(days=180)

    response = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "50",
            "expiration_date": expiration_date.isoformat(),
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_receive_shelf_life_threshold_is_configurable(
    client: AsyncClient,
    auth_headers: dict,
    test_item: Item,
):
    """The 180-day rule must come from SystemSettings (single source of
    truth shared with the frontend), not a hardcoded constant - a 45-day-out
    item, rejected under the default, must be accepted once an admin lowers
    the configured threshold below 45 days."""
    near_expiration = date.today() + timedelta(days=45)

    rejected = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "10",
            "expiration_date": near_expiration.isoformat(),
        },
    )
    assert rejected.status_code == 400

    update = await client.put(
        "/api/v1/settings/system",
        headers=auth_headers,
        json={"min_shelf_life_days": 30},
    )
    assert update.status_code == 200

    accepted = await client.post(
        "/api/v1/receiving/receive",
        headers=auth_headers,
        json={
            "item_id": str(test_item.id),
            "quantity": "10",
            "expiration_date": near_expiration.isoformat(),
        },
    )
    assert accepted.status_code == 200


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
        json={"barcode": test_item.sku},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["item"]["sku"] == test_item.sku
    assert data["item"]["name"] == test_item.name


@pytest.mark.asyncio
async def test_validate_barcode_not_found(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test barcode validation for non-existent SKU"""
    response = await client.post(
        "/api/v1/receiving/validate-barcode",
        headers=auth_headers,
        json={"barcode": "NON-EXISTENT-SKU"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["item"] is None


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


@pytest.mark.asyncio
async def test_receive_goods_retries_on_batch_number_collision(
    db_session: AsyncSession,
    test_item: Item,
    test_user: User,
):
    """Regression test for the fix: generate_batch_number's MAX(batch_number)
    read has no row lock, so a concurrent request can already have taken
    the number this call is about to generate. Previously this raised an
    unhandled IntegrityError; now receive_goods retries with a freshly
    generated number instead."""
    service = ReceivingService(db_session)

    # Simulate a concurrent receipt having already claimed the batch
    # number this call is about to compute.
    next_number = await service.generate_batch_number()
    from app.models.batch import Batch, BatchStatus

    colliding_batch = Batch(
        item_id=test_item.id,
        batch_number=next_number,
        quantity_received=Decimal("1"),
        quantity_available=Decimal("1"),
        receipt_date=date.today(),
        expiration_date=date.today() + timedelta(days=200),
        status=BatchStatus.ACTIVE,
    )
    db_session.add(colliding_batch)
    await db_session.commit()

    batch, movement, grn_number = await service.receive_goods(
        item_id=test_item.id,
        quantity=Decimal("10"),
        expiration_date=date.today() + timedelta(days=200),
        user_id=test_user.id,
    )
    await db_session.commit()

    assert batch.batch_number != next_number
    assert batch.batch_number.startswith("GR-")

