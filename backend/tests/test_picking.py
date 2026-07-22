"""Tests for picking and dispatch functionality"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.batch import Batch, BatchStatus
from app.models.customer import Customer
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem, DeliveryNoteStatus
from app.models.item import Item
from app.models.user import User, UserRole


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
    """The suggest-batches endpoint returns every available batch in FEFO
    order — batches needed for the pick carry suggested_quantity > 0, the
    rest carry 0 so the UI can still show them."""
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
    # Both batches are returned, not just the ones needed for the pick.
    assert len(data["suggestions"]) == 2
    # FEFO ordering: PICK-001 expires first (60 days) so it comes first.
    assert data["suggestions"][0]["batch_number"] == "PICK-001"
    assert data["suggestions"][0]["suggested_quantity"] == 50
    # PICK-002 is returned as a fallback option with suggested_quantity = 0.
    assert data["suggestions"][1]["batch_number"] == "PICK-002"
    assert data["suggestions"][1]["suggested_quantity"] == 0


@pytest.mark.asyncio
async def test_suggest_batches_insufficient_stock(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """When the request exceeds total available stock the endpoint still
    returns 200 with can_fulfill=False — the UI surfaces what *does* exist
    rather than a hard 400 that leaves the operator with nothing."""
    item, batches = item_with_stock

    response = await client.post(
        "/api/v1/picking/suggest-batches",
        headers=auth_headers,
        json={
            "item_id": str(item.id),
            "quantity_needed": "500",  # More than available (250)
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["can_fulfill"] is False
    assert data["total_available"] == 250
    # Both batches come back, each with their full quantity as the
    # suggested pick — the engine fills what it can even when it can't
    # fully fulfill the request.
    assert len(data["suggestions"]) == 2
    total_suggested = sum(s["suggested_quantity"] for s in data["suggestions"])
    assert total_suggested == 250


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


@pytest.fixture
async def customer_with_allocated_batch(
    db_session: AsyncSession,
    item_with_stock: tuple[Item, list[Batch]],
) -> tuple[User, str, Batch, Batch]:
    """A CUSTOMER-role user with one batch dispatched to them (allocated)
    and a second batch (from the same item_with_stock fixture) that was
    never dispatched to them - i.e. not theirs."""
    item, batches = item_with_stock
    allocated_batch, other_batch = batches[0], batches[1]

    customer = Customer(name="Consume Test Customer", address="1 Test St")
    db_session.add(customer)
    await db_session.flush()

    warehouse_user = User(
        username="consume_test_warehouse",
        email="consume_warehouse@test.com",
        hashed_password="x",
        full_name="Warehouse",
        role=UserRole.WAREHOUSE_WORKER,
        is_active=True,
    )
    db_session.add(warehouse_user)
    await db_session.flush()

    dn = DeliveryNote(
        customer_id=customer.id,
        created_by=warehouse_user.id,
        delivery_note_number="DN-TEST-CONSUME-001",
        status=DeliveryNoteStatus.ISSUED,
        is_consignment=True,
    )
    db_session.add(dn)
    await db_session.flush()

    db_session.add(
        DeliveryNoteItem(
            delivery_note_id=dn.id,
            item_id=item.id,
            batch_id=allocated_batch.id,
            quantity=Decimal("10"),
        )
    )

    customer_user = User(
        username="consume_test_customer",
        email="consume_customer@test.com",
        hashed_password="x",
        full_name="Customer",
        role=UserRole.CUSTOMER,
        customer_id=customer.id,
        is_active=True,
    )
    db_session.add(customer_user)
    await db_session.commit()
    await db_session.refresh(customer_user)

    token = create_access_token(subject=customer_user.id, role=customer_user.role.value)
    return customer_user, f"Bearer {token}", allocated_batch, other_batch


@pytest.mark.asyncio
async def test_consume_own_allocated_batch_succeeds(
    client: AsyncClient,
    customer_with_allocated_batch: tuple[User, str, Batch, Batch],
):
    """A customer can consume from a batch that was dispatched to them."""
    _, token, allocated_batch, _ = customer_with_allocated_batch

    response = await client.post(
        "/api/v1/picking/consume",
        headers={"Authorization": token},
        json={"batch_id": str(allocated_batch.id), "quantity": "5"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_consume_other_customers_batch_forbidden(
    client: AsyncClient,
    customer_with_allocated_batch: tuple[User, str, Batch, Batch],
):
    """A customer cannot consume from a batch never dispatched to them -
    this is the IDOR fix: previously any picking-authorized user could
    consume from any batch_id."""
    _, token, _, other_batch = customer_with_allocated_batch

    response = await client.post(
        "/api/v1/picking/consume",
        headers={"Authorization": token},
        json={"batch_id": str(other_batch.id), "quantity": "5"},
    )

    assert response.status_code == 403


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


@pytest.fixture
async def customer(db_session: AsyncSession) -> Customer:
    """A customer with an email on file, for dispatch + document tests."""
    customer = Customer(name="Doc Test Customer", email="customer@example.com")
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.mark.asyncio
async def test_dispatch_with_customer_creates_real_delivery_note(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
    customer: Customer,
):
    """Regression test for the fix: customer_id was accepted by the
    dispatch request but silently discarded - no DeliveryNote was ever
    created, so there was nothing to print/email later. Dispatching with a
    customer must now produce a real, persisted DeliveryNote whose number
    is the dispatch's own reference_number."""
    item, batches = item_with_stock

    response = await client.post(
        "/api/v1/picking/dispatch",
        headers=auth_headers,
        json={
            "items": [{"batch_id": str(batches[0].id), "quantity": "20"}],
            "customer_id": str(customer.id),
        },
    )

    assert response.status_code == 200
    ref_number = response.json()["reference_number"]
    assert ref_number.startswith("DN-")

    result = await db_session.execute(
        select(DeliveryNote).where(DeliveryNote.delivery_note_number == ref_number)
    )
    dn = result.scalar_one_or_none()
    assert dn is not None
    assert dn.customer_id == customer.id
    assert dn.status == DeliveryNoteStatus.ISSUED


@pytest.mark.asyncio
async def test_dispatch_without_customer_has_no_delivery_note(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """A dispatch with no customer keeps the old DSP- reference and does
    not fabricate a DeliveryNote out of nothing."""
    item, batches = item_with_stock

    response = await client.post(
        "/api/v1/picking/dispatch",
        headers=auth_headers,
        json={"items": [{"batch_id": str(batches[0].id), "quantity": "20"}]},
    )

    assert response.status_code == 200
    ref_number = response.json()["reference_number"]
    assert ref_number.startswith("DSP-")

    result = await db_session.execute(
        select(DeliveryNote).where(DeliveryNote.delivery_note_number == ref_number)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_generate_pick_note_print_returns_pdf(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """A pick note can always be produced from the dispatch's own
    movements - no customer required."""
    item, batches = item_with_stock
    dispatch = await client.post(
        "/api/v1/picking/dispatch",
        headers=auth_headers,
        json={"items": [{"batch_id": str(batches[0].id), "quantity": "20"}]},
    )
    ref_number = dispatch.json()["reference_number"]

    response = await client.post(
        f"/api/v1/picking/dispatches/{ref_number}/document",
        headers=auth_headers,
        json={"document_type": "pick_note", "action": "print"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["pdf_base64"]  # non-empty, a real PDF was produced


@pytest.mark.asyncio
async def test_generate_pick_note_unknown_reference_404(
    client: AsyncClient,
    auth_headers: dict,
):
    response = await client.post(
        "/api/v1/picking/dispatches/NO-SUCH-REF/document",
        headers=auth_headers,
        json={"document_type": "pick_note", "action": "print"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_delivery_note_without_customer_fails_gracefully(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """No customer was selected for this dispatch, so there is no delivery
    note to produce - the endpoint must say so clearly rather than 404 or
    500, since the dispatch itself is perfectly real."""
    item, batches = item_with_stock
    dispatch = await client.post(
        "/api/v1/picking/dispatch",
        headers=auth_headers,
        json={"items": [{"batch_id": str(batches[0].id), "quantity": "20"}]},
    )
    ref_number = dispatch.json()["reference_number"]

    response = await client.post(
        f"/api/v1/picking/dispatches/{ref_number}/document",
        headers=auth_headers,
        json={"document_type": "delivery_note", "action": "print"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["pdf_base64"] is None


@pytest.mark.asyncio
async def test_generate_delivery_note_with_customer_print_returns_pdf(
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
    customer: Customer,
):
    item, batches = item_with_stock
    dispatch = await client.post(
        "/api/v1/picking/dispatch",
        headers=auth_headers,
        json={
            "items": [{"batch_id": str(batches[0].id), "quantity": "20"}],
            "customer_id": str(customer.id),
        },
    )
    ref_number = dispatch.json()["reference_number"]

    response = await client.post(
        f"/api/v1/picking/dispatches/{ref_number}/document",
        headers=auth_headers,
        json={"document_type": "delivery_note", "action": "print"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["pdf_base64"]


@pytest.mark.asyncio
@patch("app.services.email_service.resend.Emails.send")
async def test_generate_delivery_note_email_sent_to_customer(
    mock_send,
    client: AsyncClient,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
    customer: Customer,
):
    mock_send.return_value = {"id": "test-id"}
    from app.services.email_service import email_service
    orig = email_service._configured
    email_service._configured = True

    try:
        item, batches = item_with_stock
        dispatch = await client.post(
            "/api/v1/picking/dispatch",
            headers=auth_headers,
            json={
                "items": [{"batch_id": str(batches[0].id), "quantity": "20"}],
                "customer_id": str(customer.id),
            },
        )
        ref_number = dispatch.json()["reference_number"]

        response = await client.post(
            f"/api/v1/picking/dispatches/{ref_number}/document",
            headers=auth_headers,
            json={"document_type": "delivery_note", "action": "email"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_send.assert_called_once()
        sent_params = mock_send.call_args[0][0]
        assert sent_params["to"] == [customer.email]
        assert len(sent_params["attachments"]) == 1
    finally:
        email_service._configured = orig


@pytest.mark.asyncio
async def test_generate_delivery_note_email_without_customer_email_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    item_with_stock: tuple[Item, list[Batch]],
):
    """The customer exists but has no email on file - a clear failure, not
    a crash or a silently-dropped send."""
    no_email_customer = Customer(name="No Email Customer")
    db_session.add(no_email_customer)
    await db_session.commit()
    await db_session.refresh(no_email_customer)

    item, batches = item_with_stock
    dispatch = await client.post(
        "/api/v1/picking/dispatch",
        headers=auth_headers,
        json={
            "items": [{"batch_id": str(batches[0].id), "quantity": "20"}],
            "customer_id": str(no_email_customer.id),
        },
    )
    ref_number = dispatch.json()["reference_number"]

    response = await client.post(
        f"/api/v1/picking/dispatches/{ref_number}/document",
        headers=auth_headers,
        json={"document_type": "delivery_note", "action": "email"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

