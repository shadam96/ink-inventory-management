"""Tests for FEFO (First Expired, First Out) engine"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.services.fefo_engine import FEFOEngine


@pytest.fixture
async def item_with_batches(db_session: AsyncSession) -> tuple[Item, list[Batch]]:
    """Create an item with multiple batches having different expiration dates"""
    item = Item(
        id=uuid4(),
        sku="FEFO-TEST-001",
        name="FEFO Test Ink",
        supplier="Test Supplier",
        unit_of_measure="KG",
        cost_price=Decimal("50.00"),
    )
    db_session.add(item)
    await db_session.flush()
    
    today = date.today()
    
    # Create batches with different expiration dates
    batches = [
        Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number="FEFO-001",
            quantity_received=Decimal("100"),
            quantity_available=Decimal("100"),
            receipt_date=today - timedelta(days=30),
            expiration_date=today + timedelta(days=20),  # Expires soon
            status=BatchStatus.ACTIVE,
        ),
        Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number="FEFO-002",
            quantity_received=Decimal("150"),
            quantity_available=Decimal("150"),
            receipt_date=today - timedelta(days=20),
            expiration_date=today + timedelta(days=90),  # Medium
            status=BatchStatus.ACTIVE,
        ),
        Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number="FEFO-003",
            quantity_received=Decimal("200"),
            quantity_available=Decimal("200"),
            receipt_date=today - timedelta(days=10),
            expiration_date=today + timedelta(days=180),  # Safe
            status=BatchStatus.ACTIVE,
        ),
    ]
    
    for batch in batches:
        db_session.add(batch)
    
    await db_session.commit()
    return item, batches


@pytest.mark.asyncio
async def test_fefo_suggests_earliest_expiring_first(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test that FEFO suggests batches with earliest expiration first"""
    item, batches = item_with_batches
    fefo = FEFOEngine(db_session)
    
    suggestions = await fefo.suggest_batches_for_picking(
        item_id=item.id,
        quantity_needed=Decimal("50"),
    )
    
    assert len(suggestions) == 1
    assert suggestions[0].batch_number == "FEFO-001"  # Earliest expiring
    assert suggestions[0].suggested_quantity == Decimal("50")


@pytest.mark.asyncio
async def test_fefo_spans_multiple_batches(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test that FEFO spans multiple batches when needed"""
    item, batches = item_with_batches
    fefo = FEFOEngine(db_session)
    
    # Request more than first batch has
    suggestions = await fefo.suggest_batches_for_picking(
        item_id=item.id,
        quantity_needed=Decimal("200"),
    )
    
    assert len(suggestions) == 2
    # First batch - earliest expiring, take all 100
    assert suggestions[0].batch_number == "FEFO-001"
    assert suggestions[0].suggested_quantity == Decimal("100")
    # Second batch - take remaining 100
    assert suggestions[1].batch_number == "FEFO-002"
    assert suggestions[1].suggested_quantity == Decimal("100")


@pytest.mark.asyncio
async def test_fefo_total_available(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test total available quantity calculation"""
    item, batches = item_with_batches
    fefo = FEFOEngine(db_session)
    
    total = await fefo.get_total_available(item.id)
    assert total == Decimal("450")  # 100 + 150 + 200


@pytest.mark.asyncio
async def test_fefo_can_fulfill(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test can_fulfill check"""
    item, batches = item_with_batches
    fefo = FEFOEngine(db_session)
    
    assert await fefo.can_fulfill(item.id, Decimal("400")) is True
    assert await fefo.can_fulfill(item.id, Decimal("450")) is True
    assert await fefo.can_fulfill(item.id, Decimal("500")) is False


@pytest.mark.asyncio
async def test_fefo_validate_picking_success(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test picking validation for valid pick"""
    item, batches = item_with_batches
    fefo = FEFOEngine(db_session)
    
    validation = await fefo.validate_picking(
        batch_id=batches[0].id,
        quantity=Decimal("50"),
    )
    
    assert validation.is_valid is True
    assert len(validation.errors) == 0


@pytest.mark.asyncio
async def test_fefo_validate_picking_insufficient_quantity(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test picking validation rejects insufficient quantity"""
    item, batches = item_with_batches
    fefo = FEFOEngine(db_session)
    
    validation = await fefo.validate_picking(
        batch_id=batches[0].id,
        quantity=Decimal("150"),  # More than available (100)
    )
    
    assert validation.is_valid is False
    assert len(validation.errors) > 0


@pytest.mark.asyncio
async def test_fefo_validate_picking_warns_fefo_violation(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test picking validation warns when skipping earlier expiring batches"""
    item, batches = item_with_batches
    fefo = FEFOEngine(db_session)
    
    # Try to pick from later-expiring batch
    validation = await fefo.validate_picking(
        batch_id=batches[2].id,  # Latest expiring
        quantity=Decimal("50"),
    )
    
    assert validation.is_valid is True  # Still valid, but with warning
    assert len(validation.warnings) > 0  # Should warn about earlier batches


@pytest.mark.asyncio
async def test_fefo_validate_picking_expired_batch(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test picking validation rejects expired batch"""
    item, batches = item_with_batches
    
    # Make first batch expired
    batches[0].expiration_date = date.today() - timedelta(days=1)
    await db_session.commit()
    
    fefo = FEFOEngine(db_session)
    
    validation = await fefo.validate_picking(
        batch_id=batches[0].id,
        quantity=Decimal("50"),
    )
    
    assert validation.is_valid is False
    assert any("פג" in err for err in validation.errors)  # Contains "expired" in Hebrew


@pytest.mark.asyncio
async def test_fefo_warning_levels(db_session: AsyncSession):
    """Test warning level classification"""
    item = Item(
        id=uuid4(),
        sku="WARN-TEST-001",
        name="Warning Test Ink",
        supplier="Test",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.flush()
    
    today = date.today()
    
    batches = [
        Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number="WARN-CRITICAL",
            quantity_received=Decimal("10"),
            quantity_available=Decimal("10"),
            receipt_date=today,
            expiration_date=today + timedelta(days=15),  # < 30 days = critical
            status=BatchStatus.ACTIVE,
        ),
        Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number="WARN-WARNING",
            quantity_received=Decimal("10"),
            quantity_available=Decimal("10"),
            receipt_date=today,
            expiration_date=today + timedelta(days=45),  # 30-60 days = warning
            status=BatchStatus.ACTIVE,
        ),
        Batch(
            id=uuid4(),
            item_id=item.id,
            batch_number="WARN-SAFE",
            quantity_received=Decimal("10"),
            quantity_available=Decimal("10"),
            receipt_date=today,
            expiration_date=today + timedelta(days=120),  # > 90 days = safe
            status=BatchStatus.ACTIVE,
        ),
    ]
    
    for batch in batches:
        db_session.add(batch)
    await db_session.commit()
    
    fefo = FEFOEngine(db_session)
    suggestions = await fefo.suggest_batches_for_picking(
        item_id=item.id,
        quantity_needed=Decimal("30"),
    )
    
    assert suggestions[0].warning_level == "critical"
    assert suggestions[1].warning_level == "warning"
    assert suggestions[2].warning_level == "safe"


@pytest.mark.asyncio
async def test_fefo_expiration_summary(
    db_session: AsyncSession,
    item_with_batches: tuple[Item, list[Batch]],
):
    """Test expiration summary calculation"""
    item, batches = item_with_batches
    fefo = FEFOEngine(db_session)
    
    summary = await fefo.get_expiration_summary(item.id)
    
    assert summary["total_quantity"] == Decimal("450")
    assert summary["total_batches"] == 3
    assert summary["critical"]["batches"] == 1  # FEFO-001 (20 days)

