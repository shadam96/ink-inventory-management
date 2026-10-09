"""Tests for AccessScope-based location/customer data scoping.

Covers: opt-in location scoping for staff (MANAGER/WAREHOUSE_WORKER/VIEWER),
and the CUSTOMER-role gap this closes - customers could previously reach
batches/movements/locations/dashboard/alerts endpoints directly (they were
only kept away from those pages at the frontend routing layer, not the API).
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.location import Location
from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from app.models.movement import Movement, MovementType
from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.customer import Customer


def _headers(user: User) -> dict:
    token = create_access_token(subject=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def scoping_world(db_session: AsyncSession):
    """Two locations (A, B), one item with a batch at each, a movement and
    a batch-level alert at each location, plus one item-only alert (not
    attributable to a single location)."""
    location_a = Location(
        warehouse="WH1", shelf="A1", position="1", location_code="SCOPE-WH-A"
    )
    location_b = Location(
        warehouse="WH1", shelf="B1", position="1", location_code="SCOPE-WH-B"
    )
    db_session.add_all([location_a, location_b])
    await db_session.flush()

    item = Item(
        sku="SCOPE-ITEM-001",
        name="Scope Test Ink",
        supplier="Test Supplier",
        unit_of_measure="kg",
        cost_price=Decimal("10.00"),
    )
    db_session.add(item)
    await db_session.flush()

    batch_a = Batch(
        batch_number="SCOPE-BT-A",
        item_id=item.id,
        location_id=location_a.id,
        expiration_date=date.today() + timedelta(days=90),
        receipt_date=date.today(),
        quantity_received=Decimal("50"),
        quantity_available=Decimal("50"),
        status=BatchStatus.ACTIVE,
    )
    batch_b = Batch(
        batch_number="SCOPE-BT-B",
        item_id=item.id,
        location_id=location_b.id,
        expiration_date=date.today() + timedelta(days=90),
        receipt_date=date.today(),
        quantity_received=Decimal("30"),
        quantity_available=Decimal("30"),
        status=BatchStatus.ACTIVE,
    )
    db_session.add_all([batch_a, batch_b])
    await db_session.flush()

    admin_for_movements = User(
        username="scope_movement_actor",
        email="scope_movement_actor@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Movement Actor",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_for_movements)
    await db_session.flush()

    movement_a = Movement(
        batch_id=batch_a.id,
        user_id=admin_for_movements.id,
        movement_type=MovementType.RECEIPT,
        quantity=Decimal("50"),
        quantity_before=Decimal("0"),
        quantity_after=Decimal("50"),
    )
    movement_b = Movement(
        batch_id=batch_b.id,
        user_id=admin_for_movements.id,
        movement_type=MovementType.RECEIPT,
        quantity=Decimal("30"),
        quantity_before=Decimal("0"),
        quantity_after=Decimal("30"),
    )
    db_session.add_all([movement_a, movement_b])

    alert_a = Alert(
        alert_type=AlertType.EXPIRATION_WARNING,
        severity=AlertSeverity.WARNING,
        batch_id=batch_a.id,
        item_id=item.id,
        title="Batch A expiring",
        message="Batch A expiring soon",
    )
    alert_b = Alert(
        alert_type=AlertType.EXPIRATION_WARNING,
        severity=AlertSeverity.WARNING,
        batch_id=batch_b.id,
        item_id=item.id,
        title="Batch B expiring",
        message="Batch B expiring soon",
    )
    alert_item_only = Alert(
        alert_type=AlertType.LOW_STOCK,
        severity=AlertSeverity.INFO,
        item_id=item.id,
        title="Item low stock",
        message="Item low stock somewhere",
    )
    db_session.add_all([alert_a, alert_b, alert_item_only])

    admin_user = User(
        username="scope_admin",
        email="scope_admin@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Scope Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    unassigned_worker = User(
        username="scope_unassigned_worker",
        email="scope_unassigned_worker@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Unassigned Worker",
        role=UserRole.WAREHOUSE_WORKER,
        is_active=True,
    )
    scoped_worker = User(
        username="scope_scoped_worker",
        email="scope_scoped_worker@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Scoped Worker",
        role=UserRole.WAREHOUSE_WORKER,
        is_active=True,
        locations=[location_a],
    )
    customer = Customer(name="Scope Customer", address="1 Scope St")
    db_session.add_all([admin_user, unassigned_worker, scoped_worker, customer])
    await db_session.flush()

    customer_user = User(
        username="scope_customer_user",
        email="scope_customer_user@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Scope Customer User",
        role=UserRole.CUSTOMER,
        customer_id=customer.id,
        is_active=True,
    )
    db_session.add(customer_user)

    await db_session.commit()
    await db_session.refresh(scoped_worker)
    await db_session.refresh(admin_user)
    await db_session.refresh(unassigned_worker)
    await db_session.refresh(customer_user)

    return {
        "location_a": location_a,
        "location_b": location_b,
        "item": item,
        "batch_a": batch_a,
        "batch_b": batch_b,
        "customer": customer,
        "admin_headers": _headers(admin_user),
        "unassigned_worker_headers": _headers(unassigned_worker),
        "scoped_worker_headers": _headers(scoped_worker),
        "customer_headers": _headers(customer_user),
    }


async def _create_delivery_note(client: AsyncClient, world: dict, batch: Batch) -> dict:
    """Create a DN for world's customer as admin (no stock movement)."""
    response = await client.post(
        "/api/v1/delivery-notes",
        json={
            "customer_id": str(world["customer"].id),
            "items": [{"batch_id": str(batch.id), "quantity": 5}],
        },
        headers=world["admin_headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_admin_sees_batches_across_all_locations(client: AsyncClient, scoping_world):
    response = await client.get(
        "/api/v1/batches", headers=scoping_world["admin_headers"]
    )
    assert response.status_code == 200
    batch_numbers = {b["batch_number"] for b in response.json()["items"]}
    assert {"SCOPE-BT-A", "SCOPE-BT-B"} <= batch_numbers


@pytest.mark.asyncio
async def test_unassigned_staff_sees_all_locations(client: AsyncClient, scoping_world):
    """Regression guard for the opt-in scoping design: a staff user with no
    location assignments must keep today's full-access behavior."""
    response = await client.get(
        "/api/v1/batches", headers=scoping_world["unassigned_worker_headers"]
    )
    assert response.status_code == 200
    batch_numbers = {b["batch_number"] for b in response.json()["items"]}
    assert {"SCOPE-BT-A", "SCOPE-BT-B"} <= batch_numbers


@pytest.mark.asyncio
async def test_scoped_worker_only_sees_assigned_location_batches(
    client: AsyncClient, scoping_world
):
    headers = scoping_world["scoped_worker_headers"]

    response = await client.get("/api/v1/batches", headers=headers)
    assert response.status_code == 200
    batch_numbers = {b["batch_number"] for b in response.json()["items"]}
    assert "SCOPE-BT-A" in batch_numbers
    assert "SCOPE-BT-B" not in batch_numbers

    # Direct-ID access to the out-of-scope batch 404s, not 403 (matches the
    # existing not-found-not-forbidden convention elsewhere in the codebase).
    other_response = await client.get(
        f"/api/v1/batches/{scoping_world['batch_b'].id}", headers=headers
    )
    assert other_response.status_code == 404

    own_response = await client.get(
        f"/api/v1/batches/{scoping_world['batch_a'].id}", headers=headers
    )
    assert own_response.status_code == 200


@pytest.mark.asyncio
async def test_scoped_worker_movement_history_filtered(
    client: AsyncClient, scoping_world
):
    response = await client.get(
        "/api/v1/movements", headers=scoping_world["scoped_worker_headers"]
    )
    assert response.status_code == 200
    batch_ids = {m["batch_id"] for m in response.json()["movements"]}
    assert str(scoping_world["batch_a"].id) in batch_ids
    assert str(scoping_world["batch_b"].id) not in batch_ids


@pytest.mark.asyncio
async def test_scoped_worker_locations_list_filtered(
    client: AsyncClient, scoping_world
):
    response = await client.get(
        "/api/v1/locations", headers=scoping_world["scoped_worker_headers"]
    )
    assert response.status_code == 200
    location_codes = {loc["location_code"] for loc in response.json()["items"]}
    assert location_codes == {"SCOPE-WH-A"}


@pytest.mark.asyncio
async def test_scoped_worker_dashboard_kpis_reflect_only_assigned_location(
    client: AsyncClient, db_session: AsyncSession, scoping_world
):
    admin_response = await client.get(
        "/api/v1/dashboard/kpis", headers=scoping_world["admin_headers"]
    )
    assert admin_response.status_code == 200

    # The test client's `client` fixture shares one AsyncSession across every
    # request in this test (unlike production, where app.core.database.get_db
    # hands each request a brand-new session) - so the admin call above
    # leaves Item.batches loaded unfiltered in the session's identity map.
    # Without expiring it, the next request would see that stale, already
    # -loaded collection instead of a freshly location-filtered one. This
    # has no equivalent in production, where every request already starts
    # from a clean session.
    db_session.expire_all()

    scoped_response = await client.get(
        "/api/v1/dashboard/kpis", headers=scoping_world["scoped_worker_headers"]
    )
    assert scoped_response.status_code == 200

    admin_totals = admin_response.json()["inventory_value_by_currency"]
    scoped_totals = scoped_response.json()["inventory_value_by_currency"]

    # Admin sees both batches (50 + 30 = 80 units * 10.00 = 800.00 ILS),
    # the scoped worker only sees location A's batch (50 * 10.00 = 500.00).
    assert admin_totals["ILS"] == pytest.approx(800.00)
    assert scoped_totals["ILS"] == pytest.approx(500.00)


@pytest.mark.asyncio
async def test_scoped_worker_alerts_exclude_other_location_and_item_only_alerts(
    client: AsyncClient, scoping_world
):
    response = await client.get(
        "/api/v1/alerts", headers=scoping_world["scoped_worker_headers"]
    )
    assert response.status_code == 200
    titles = {a["title"] for a in response.json()["items"]}
    assert "Batch A expiring" in titles
    assert "Batch B expiring" not in titles
    assert "Item low stock" not in titles


@pytest.mark.asyncio
async def test_customer_gets_403_on_staff_endpoints(client: AsyncClient, scoping_world):
    """The confirmed security gap being closed: a CUSTOMER-role user could
    previously reach every staff endpoint directly (only the frontend
    routing kept them off those pages)."""
    headers = scoping_world["customer_headers"]

    for method, path in [
        ("GET", "/api/v1/batches"),
        ("GET", "/api/v1/movements"),
        ("GET", "/api/v1/locations"),
        ("GET", "/api/v1/dashboard/kpis"),
        ("GET", "/api/v1/alerts"),
    ]:
        response = await client.request(method, path, headers=headers)
        assert response.status_code == 403, f"{method} {path} should be 403 for a customer"


@pytest.mark.asyncio
async def test_customer_still_reaches_inventory(client: AsyncClient, scoping_world):
    """Sanity check: closing the staff-endpoint gap must not regress the
    endpoints that are intentionally customer-facing (inventory_view.py's
    customer branch, which stays on the CurrentUser gate, not StaffUser)."""
    headers = scoping_world["customer_headers"]

    inventory_response = await client.get("/api/v1/inventory", headers=headers)
    assert inventory_response.status_code == 200

    total_cost_response = await client.get(
        "/api/v1/inventory/total-cost", headers=headers
    )
    assert total_cost_response.status_code == 200


# ---------------------------------------------------------------------------
# Picking honors location scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scoped_worker_picking_suggestions_only_include_assigned_location(
    client: AsyncClient, scoping_world
):
    payload = {"item_id": str(scoping_world["item"].id), "quantity_needed": 0}

    admin_response = await client.post(
        "/api/v1/picking/suggest-batches", json=payload, headers=scoping_world["admin_headers"]
    )
    assert admin_response.status_code == 200
    assert {s["batch_number"] for s in admin_response.json()["suggestions"]} == {
        "SCOPE-BT-A",
        "SCOPE-BT-B",
    }

    response = await client.post(
        "/api/v1/picking/suggest-batches",
        json=payload,
        headers=scoping_world["scoped_worker_headers"],
    )
    assert response.status_code == 200
    body = response.json()
    for key in ("suggestions", "fifo_suggestions", "lifo_suggestions"):
        assert {s["batch_number"] for s in body[key]} == {"SCOPE-BT-A"}, key
    assert body["total_available"] == 50


@pytest.mark.asyncio
async def test_scoped_worker_cannot_pick_out_of_scope_batch(
    client: AsyncClient, db_session: AsyncSession, scoping_world
):
    """Every picking write path rejects an out-of-scope batch exactly like a
    nonexistent one, and leaves its stock untouched."""
    headers = scoping_world["scoped_worker_headers"]
    batch_b = scoping_world["batch_b"]

    for path, payload in [
        ("/api/v1/picking/validate-pick", {"batch_id": str(batch_b.id), "quantity": 1}),
        ("/api/v1/picking/execute-pick", {"batch_id": str(batch_b.id), "quantity": 1}),
        ("/api/v1/picking/dispatch", {"items": [{"batch_id": str(batch_b.id), "quantity": 1}]}),
        ("/api/v1/picking/consume", {"batch_id": str(batch_b.id), "quantity": 1}),
    ]:
        response = await client.post(path, json=payload, headers=headers)
        assert response.status_code == 400, path
        assert response.json()["detail"]["errors"] == ["אצווה לא נמצאה"], path

    await db_session.refresh(batch_b)
    assert batch_b.quantity_available == Decimal("30")

    own_response = await client.post(
        "/api/v1/picking/execute-pick",
        json={"batch_id": str(scoping_world["batch_a"].id), "quantity": 1},
        headers=headers,
    )
    assert own_response.status_code == 200


@pytest.mark.asyncio
async def test_scoped_worker_fefo_warning_ignores_out_of_scope_batches(
    client: AsyncClient, db_session: AsyncSession, scoping_world
):
    """An earlier-expiring batch the worker can't see or pick must not
    trigger a FEFO-violation warning (or leak its batch number)."""
    db_session.add(
        Batch(
            batch_number="SCOPE-BT-B-EARLY",
            item_id=scoping_world["item"].id,
            location_id=scoping_world["location_b"].id,
            expiration_date=date.today() + timedelta(days=45),
            receipt_date=date.today(),
            quantity_received=Decimal("10"),
            quantity_available=Decimal("10"),
            status=BatchStatus.ACTIVE,
        )
    )
    await db_session.commit()
    payload = {"batch_id": str(scoping_world["batch_a"].id), "quantity": 1}

    admin_response = await client.post(
        "/api/v1/picking/validate-pick", json=payload, headers=scoping_world["admin_headers"]
    )
    assert any("SCOPE-BT-B-EARLY" in w for w in admin_response.json()["warnings"])

    response = await client.post(
        "/api/v1/picking/validate-pick",
        json=payload,
        headers=scoping_world["scoped_worker_headers"],
    )
    assert response.status_code == 200
    assert not any("SCOPE-BT-B-EARLY" in w for w in response.json()["warnings"])


@pytest.mark.asyncio
async def test_scoped_worker_expiration_summary_only_counts_assigned_location(
    client: AsyncClient, scoping_world
):
    response = await client.get(
        f"/api/v1/picking/expiration-summary/{scoping_world['item'].id}",
        headers=scoping_world["scoped_worker_headers"],
    )
    assert response.status_code == 200
    assert response.json()["total_quantity"] == 50
    assert response.json()["total_batches"] == 1


@pytest.mark.asyncio
async def test_scoped_worker_cannot_print_out_of_scope_pick_note(
    client: AsyncClient, scoping_world
):
    async def dispatch_as_admin(batch: Batch) -> str:
        response = await client.post(
            "/api/v1/picking/dispatch",
            json={"items": [{"batch_id": str(batch.id), "quantity": 1}]},
            headers=scoping_world["admin_headers"],
        )
        assert response.status_code == 200, response.text
        return response.json()["reference_number"]

    ref_a = await dispatch_as_admin(scoping_world["batch_a"])
    ref_b = await dispatch_as_admin(scoping_world["batch_b"])
    headers = scoping_world["scoped_worker_headers"]
    body = {"document_type": "pick_note", "action": "print"}

    other_response = await client.post(
        f"/api/v1/picking/dispatches/{ref_b}/document", json=body, headers=headers
    )
    assert other_response.status_code == 404

    own_response = await client.post(
        f"/api/v1/picking/dispatches/{ref_a}/document", json=body, headers=headers
    )
    assert own_response.status_code == 200
    assert own_response.json()["success"] is True


@pytest.mark.asyncio
async def test_scoped_worker_items_stock_counts_only_assigned_location(
    client: AsyncClient, db_session: AsyncSession, scoping_world
):
    """The picking screen greys out items by /items stock, so it has to
    agree with the (scoped) batch suggestions."""
    response = await client.get(
        f"/api/v1/items/{scoping_world['item'].id}",
        headers=scoping_world["scoped_worker_headers"],
    )
    assert response.status_code == 200
    assert float(response.json()["total_quantity_available"]) == 50

    db_session.expire_all()  # see test_scoped_worker_dashboard_kpis_... above
    list_response = await client.get(
        "/api/v1/items", headers=scoping_world["scoped_worker_headers"]
    )
    row = next(i for i in list_response.json()["items"] if i["sku"] == "SCOPE-ITEM-001")
    assert float(row["total_quantity_available"]) == 50


# ---------------------------------------------------------------------------
# Delivery notes honor location scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scoped_worker_only_sees_delivery_notes_for_assigned_location(
    client: AsyncClient, scoping_world
):
    dn_a = await _create_delivery_note(client, scoping_world, scoping_world["batch_a"])
    dn_b = await _create_delivery_note(client, scoping_world, scoping_world["batch_b"])
    headers = scoping_world["scoped_worker_headers"]

    list_response = await client.get("/api/v1/delivery-notes", headers=headers)
    assert list_response.status_code == 200
    assert {dn["id"] for dn in list_response.json()["items"]} == {dn_a["id"]}

    for method, path, kwargs in [
        ("GET", f"/api/v1/delivery-notes/{dn_b['id']}", {}),
        ("GET", f"/api/v1/delivery-notes/{dn_b['id']}/pdf", {}),
        ("PUT", f"/api/v1/delivery-notes/{dn_b['id']}/status", {"json": {"status": "issued"}}),
    ]:
        response = await client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == 404, f"{method} {path}"

    own_response = await client.get(f"/api/v1/delivery-notes/{dn_a['id']}", headers=headers)
    assert own_response.status_code == 200


@pytest.mark.asyncio
async def test_scoped_worker_cannot_put_out_of_scope_batch_on_delivery_note(
    client: AsyncClient, db_session: AsyncSession, scoping_world
):
    response = await client.post(
        "/api/v1/delivery-notes",
        json={
            "customer_id": str(scoping_world["customer"].id),
            "items": [{"batch_id": str(scoping_world["batch_b"].id), "quantity": 1}],
        },
        headers=scoping_world["scoped_worker_headers"],
    )
    assert response.status_code == 400

    # In production get_db rolls the failed request back; the test client
    # shares one session across requests, so do that rollback here.
    await db_session.rollback()
    list_response = await client.get(
        "/api/v1/delivery-notes", headers=scoping_world["admin_headers"]
    )
    assert list_response.json()["total"] == 0

