"""Tests for the admin-only user-management endpoints (users.py)."""
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.location import Location


@pytest.fixture
async def sample_location(db_session: AsyncSession) -> Location:
    location = Location(
        warehouse="USR-WH", shelf="1", position="1", location_code="USR-TEST-LOC"
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest.fixture
async def managed_user(db_session: AsyncSession) -> User:
    user = User(
        username="managed_user",
        email="managed_user@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Managed User",
        role=UserRole.WAREHOUSE_WORKER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_admin_can_list_users(
    client: AsyncClient, admin_headers: dict, managed_user: User
):
    response = await client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()["items"]}
    assert "managed_user" in usernames


@pytest.mark.parametrize(
    "role",
    [UserRole.MANAGER, UserRole.WAREHOUSE_WORKER, UserRole.VIEWER, UserRole.CUSTOMER],
)
@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(
    client: AsyncClient, db_session: AsyncSession, role: UserRole
):
    from app.core.security import create_access_token

    non_admin = User(
        username=f"non_admin_{role.value}",
        email=f"non_admin_{role.value}@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Non Admin",
        role=role,
        is_active=True,
    )
    db_session.add(non_admin)
    await db_session.commit()
    await db_session.refresh(non_admin)

    token = create_access_token(subject=non_admin.id, role=non_admin.role.value)
    response = await client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_update_user_role(
    client: AsyncClient, admin_headers: dict, managed_user: User
):
    response = await client.put(
        f"/api/v1/users/{managed_user.id}",
        headers=admin_headers,
        json={"role": "manager"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "manager"


@pytest.mark.asyncio
async def test_admin_can_assign_locations_to_user(
    client: AsyncClient,
    admin_headers: dict,
    managed_user: User,
    sample_location: Location,
):
    response = await client.put(
        f"/api/v1/users/{managed_user.id}/locations",
        headers=admin_headers,
        json={"location_ids": [str(sample_location.id)]},
    )
    assert response.status_code == 200
    assert response.json()["location_ids"] == [str(sample_location.id)]


@pytest.mark.asyncio
async def test_assigning_location_scopes_subsequent_batch_access(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict,
    managed_user: User,
    sample_location: Location,
):
    """End-to-end: assigning a location via this API actually changes what
    a subsequent /batches call returns for that user - ties the
    user-management endpoints to the AccessScope machinery in deps.py."""
    from datetime import date, timedelta
    from app.models.item import Item
    from app.models.batch import Batch, BatchStatus
    from app.core.security import create_access_token

    other_location = Location(
        warehouse="USR-WH2", shelf="1", position="1", location_code="USR-OTHER-LOC"
    )
    db_session.add(other_location)
    await db_session.flush()

    item = Item(
        sku="USR-SCOPE-ITEM",
        name="User Scope Test Ink",
        supplier="Test Supplier",
        unit_of_measure="kg",
        cost_price=Decimal("5.00"),
    )
    db_session.add(item)
    await db_session.flush()

    batch_in_scope = Batch(
        batch_number="USR-SCOPE-BT-IN",
        item_id=item.id,
        location_id=sample_location.id,
        expiration_date=date.today() + timedelta(days=90),
        receipt_date=date.today(),
        quantity_received=Decimal("10"),
        quantity_available=Decimal("10"),
        status=BatchStatus.ACTIVE,
    )
    batch_out_of_scope = Batch(
        batch_number="USR-SCOPE-BT-OUT",
        item_id=item.id,
        location_id=other_location.id,
        expiration_date=date.today() + timedelta(days=90),
        receipt_date=date.today(),
        quantity_received=Decimal("10"),
        quantity_available=Decimal("10"),
        status=BatchStatus.ACTIVE,
    )
    db_session.add_all([batch_in_scope, batch_out_of_scope])
    await db_session.commit()

    token = create_access_token(
        subject=managed_user.id, role=managed_user.role.value
    )
    worker_headers = {"Authorization": f"Bearer {token}"}

    before_response = await client.get("/api/v1/batches", headers=worker_headers)
    before_numbers = {b["batch_number"] for b in before_response.json()["items"]}
    assert "USR-SCOPE-BT-IN" in before_numbers
    assert "USR-SCOPE-BT-OUT" in before_numbers

    assign_response = await client.put(
        f"/api/v1/users/{managed_user.id}/locations",
        headers=admin_headers,
        json={"location_ids": [str(sample_location.id)]},
    )
    assert assign_response.status_code == 200

    db_session.expire_all()

    after_response = await client.get("/api/v1/batches", headers=worker_headers)
    after_numbers = {b["batch_number"] for b in after_response.json()["items"]}
    assert "USR-SCOPE-BT-IN" in after_numbers
    assert "USR-SCOPE-BT-OUT" not in after_numbers


@pytest.mark.asyncio
async def test_assign_nonexistent_location_returns_404_with_clear_message(
    client: AsyncClient, admin_headers: dict, managed_user: User
):
    fake_location_id = uuid4()
    response = await client.put(
        f"/api/v1/users/{managed_user.id}/locations",
        headers=admin_headers,
        json={"location_ids": [str(fake_location_id)]},
    )
    assert response.status_code == 404
    assert str(fake_location_id) in response.json()["detail"]
