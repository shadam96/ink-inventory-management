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
from app.services.inventory_service import InventoryService


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
async def test_adjust_quantity_sets_exact_target(
    db_session: AsyncSession,
    test_user: User,
    item_with_movements: tuple[Item, Batch, list[Movement]],
):
    """adjust_quantity must land the batch on exactly new_quantity.

    Regression test for the fix that made the initial read use
    with_for_update(): the row lock must be acquired starting from this
    read (not just inside record_movement's internal re-read) so the
    delta is computed against the same value record_movement will apply
    it to under concurrent access."""
    _, batch, _ = item_with_movements
    assert batch.quantity_available == Decimal("70")

    service = InventoryService(db_session)
    movement = await service.adjust_quantity(
        batch_id=batch.id,
        new_quantity=Decimal("55"),
        user_id=test_user.id,
        reason="Physical count",
    )
    await db_session.commit()

    assert movement.quantity_after == Decimal("55")
    await db_session.refresh(batch)
    assert batch.quantity_available == Decimal("55")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "movement_type",
    [MovementType.RECEIPT, MovementType.DISPATCH, MovementType.CONSUMPTION, MovementType.SCRAP],
)
async def test_record_movement_rejects_non_positive_quantity(
    db_session: AsyncSession,
    test_user: User,
    item_with_movements: tuple[Item, Batch, list[Movement]],
    movement_type: MovementType,
):
    """Defense-in-depth regression test: every movement type except
    ADJUSTMENT must reject quantity <= 0 at the service layer itself, not
    just rely on the HTTP layer's Pydantic Field(gt=0). Previously a
    negative quantity passed to e.g. DISPATCH would silently *increase*
    stock (quantity_before - negative), with the sign inversion hidden in
    the audit trail by storing abs(quantity)."""
    _, batch, _ = item_with_movements
    service = InventoryService(db_session)

    with pytest.raises(ValueError, match="כמות חייבת להיות חיובית"):
        await service.record_movement(
            batch_id=batch.id,
            movement_type=movement_type,
            quantity=Decimal("-5"),
            user_id=test_user.id,
        )


@pytest.mark.asyncio
async def test_record_movement_adjustment_allows_negative_quantity(
    db_session: AsyncSession,
    test_user: User,
    item_with_movements: tuple[Item, Batch, list[Movement]],
):
    """ADJUSTMENT is the one movement type that legitimately carries a
    signed (possibly negative) delta and must not be rejected by the new
    positive-quantity guard."""
    _, batch, _ = item_with_movements
    service = InventoryService(db_session)

    movement = await service.record_movement(
        batch_id=batch.id,
        movement_type=MovementType.ADJUSTMENT,
        quantity=Decimal("-10"),
        user_id=test_user.id,
    )
    assert movement.quantity_after == batch.quantity_available == Decimal("60")


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

