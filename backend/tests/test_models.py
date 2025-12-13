"""Tests for database models"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.item import Item
from app.models.batch import Batch, BatchStatus
from app.models.location import Location
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_user_creation(db_session: AsyncSession):
    """Test user model creation"""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("password"),
        role=UserRole.MANAGER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    assert user.id is not None
    assert user.username == "testuser"
    assert user.is_active is True
    assert user.is_manager is True
    assert user.can_modify_inventory is True


@pytest.mark.asyncio
async def test_item_creation(db_session: AsyncSession):
    """Test item model creation"""
    item = Item(
        sku="INK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
        cost_price=Decimal("50.00"),
        reorder_point=10,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    assert item.id is not None
    assert item.sku == "INK-001"
    assert item.cost_price == Decimal("50.00")


@pytest.mark.asyncio
async def test_batch_creation(db_session: AsyncSession):
    """Test batch model creation"""
    # Create item first
    item = Item(
        sku="INK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
        cost_price=Decimal("50.00"),
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    # Create batch
    batch = Batch(
        item_id=item.id,
        batch_number="GR-241212-001",
        quantity_received=Decimal("100.00"),
        quantity_available=Decimal("100.00"),
        receipt_date=date.today(),
        expiration_date=date.today() + timedelta(days=365),
    )
    db_session.add(batch)
    await db_session.commit()
    await db_session.refresh(batch)
    
    assert batch.id is not None
    assert batch.status == BatchStatus.ACTIVE
    assert not batch.is_expired
    assert batch.days_until_expiration == 365


@pytest.mark.asyncio
async def test_batch_expiration(db_session: AsyncSession):
    """Test batch expiration detection"""
    item = Item(
        sku="INK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    # Create expired batch
    batch = Batch(
        item_id=item.id,
        batch_number="GR-241212-002",
        quantity_received=Decimal("50.00"),
        quantity_available=Decimal("50.00"),
        receipt_date=date.today() - timedelta(days=400),
        expiration_date=date.today() - timedelta(days=1),
    )
    db_session.add(batch)
    await db_session.commit()
    await db_session.refresh(batch)
    
    assert batch.is_expired is True
    assert batch.days_until_expiration == -1


@pytest.mark.asyncio
async def test_batch_can_pick(db_session: AsyncSession):
    """Test batch picking validation"""
    item = Item(
        sku="INK-001",
        name="Black Ink",
        supplier="Supplier A",
        unit_of_measure="KG",
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    batch = Batch(
        item_id=item.id,
        batch_number="GR-241212-003",
        quantity_received=Decimal("100.00"),
        quantity_available=Decimal("100.00"),
        receipt_date=date.today(),
        expiration_date=date.today() + timedelta(days=90),
    )
    db_session.add(batch)
    await db_session.commit()
    
    assert batch.can_pick(Decimal("50.00")) is True
    assert batch.can_pick(Decimal("100.00")) is True
    assert batch.can_pick(Decimal("150.00")) is False


@pytest.mark.asyncio
async def test_location_code_generation():
    """Test location code generation"""
    code = Location.generate_location_code("WH1", "A", "01")
    assert code == "WH1-A-01"


@pytest.mark.asyncio
async def test_batch_number_generation():
    """Test batch number auto-generation"""
    batch_number = Batch.generate_batch_number()
    assert batch_number.startswith("GR-")
    assert len(batch_number) == 13  # GR-YYMMDD-XXX


