"""Tests for the batch update endpoint, including optimistic locking."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch, BatchStatus
from app.models.item import Item


@pytest.fixture
async def sample_batch(db_session: AsyncSession) -> Batch:
    item = Item(
        sku="BATCH-TEST-001",
        name="Batch Test Ink",
        supplier="Test Supplier",
        unit_of_measure="KG",
        cost_price=Decimal("10.00"),
    )
    db_session.add(item)
    await db_session.flush()

    batch = Batch(
        batch_number="BT-UPDATE-001",
        item_id=item.id,
        expiration_date=date.today() + timedelta(days=90),
        receipt_date=date.today(),
        quantity_received=Decimal("100"),
        quantity_available=Decimal("100"),
        status=BatchStatus.ACTIVE,
    )
    db_session.add(batch)
    await db_session.commit()
    await db_session.refresh(batch)
    return batch


@pytest.mark.asyncio
async def test_update_batch_without_version_succeeds(
    client: AsyncClient, auth_headers: dict, sample_batch: Batch
):
    """Callers that don't supply a version are unaffected (backward compat)."""
    response = await client.put(
        f"/api/v1/batches/{sample_batch.id}",
        headers=auth_headers,
        json={"notes": "updated without version"},
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "updated without version"


@pytest.mark.asyncio
async def test_update_batch_with_correct_version_succeeds(
    client: AsyncClient, auth_headers: dict, sample_batch: Batch
):
    """Supplying the current version succeeds and the version increments."""
    # Capture the version as a plain int up front - client and app share
    # the same db_session in tests, so sample_batch is the identity-mapped
    # object the request handler mutates in place; reading
    # sample_batch.version *after* the request would already reflect the
    # post-update value.
    original_version = sample_batch.version

    response = await client.put(
        f"/api/v1/batches/{sample_batch.id}",
        headers=auth_headers,
        json={"notes": "updated with correct version", "version": original_version},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "updated with correct version"
    assert data["version"] == original_version + 1


@pytest.mark.asyncio
async def test_update_batch_with_stale_version_is_rejected(
    client: AsyncClient, auth_headers: dict, sample_batch: Batch
):
    """Regression test for the fix: previously `version` was incremented
    unconditionally with nothing to compare it against, so this concurrent
    edit would have silently succeeded and clobbered the first writer's
    change instead of returning a conflict."""
    original_version = sample_batch.version

    # First writer updates successfully, bumping the version.
    first = await client.put(
        f"/api/v1/batches/{sample_batch.id}",
        headers=auth_headers,
        json={"notes": "first writer", "version": original_version},
    )
    assert first.status_code == 200

    # Second writer still has the OLD version (read before the first
    # writer's update) and tries to apply their own change on top of it.
    second = await client.put(
        f"/api/v1/batches/{sample_batch.id}",
        headers=auth_headers,
        json={"notes": "second writer (stale)", "version": original_version},
    )
    assert second.status_code == 409

    # The first writer's change must still be intact.
    get_response = await client.get(
        f"/api/v1/batches/{sample_batch.id}", headers=auth_headers
    )
    assert get_response.json()["notes"] == "first writer"
