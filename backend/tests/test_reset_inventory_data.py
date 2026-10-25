"""Tests for reset_inventory_data.py"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.models import (
    Alert,
    Batch,
    Customer,
    CustomerMachine,
    DeliveryNote,
    DeliveryNoteItem,
    Item,
    Location,
    Movement,
    SystemSettings,
    User,
)
from app.models.alert import AlertType
from app.models.movement import MovementType
from reset_inventory_data import count_rows, reset_inventory_data


async def test_reset_deletes_stock_data_and_keeps_setup(db_session, test_user):
    item = Item(sku="INK-RESET-001", name="Reset Black", supplier="Supplier")
    location = Location(warehouse="WH1", shelf="A", position="1", location_code="WH1-A-1")
    customer = Customer(name="Customer", machines=[CustomerMachine(machine_type="Press")])
    db_session.add_all([item, location, customer, SystemSettings(id=1)])
    await db_session.flush()

    batch = Batch(
        item_id=item.id,
        location_id=location.id,
        batch_number="GR-260101-001",
        quantity_received=Decimal("10"),
        quantity_available=Decimal("6"),
        receipt_date=date.today(),
        expiration_date=date.today() + timedelta(days=365),
    )
    db_session.add(batch)
    await db_session.flush()

    note = DeliveryNote(
        customer_id=customer.id,
        created_by=test_user.id,
        delivery_note_number="DN-260101-0001",
        items=[DeliveryNoteItem(item_id=item.id, batch_id=batch.id, quantity=Decimal("4"))],
    )
    db_session.add_all([
        note,
        Movement(
            batch_id=batch.id,
            user_id=test_user.id,
            movement_type=MovementType.RECEIPT,
            quantity=Decimal("10"),
            quantity_before=Decimal("0"),
            quantity_after=Decimal("10"),
        ),
        Alert(alert_type=AlertType.LOW_STOCK, item_id=item.id, title="Low", message="Low"),
        Alert(alert_type=AlertType.EXPIRED, batch_id=batch.id, title="Expired", message="Expired"),
    ])
    await db_session.commit()

    assert await count_rows(db_session) == {
        "alerts": 2,
        "delivery_note_items": 1,
        "delivery_notes": 1,
        "movements": 1,
        "batches": 1,
        "items": 1,
    }

    await reset_inventory_data(db_session)

    async def count(model):
        return await db_session.scalar(select(func.count()).select_from(model))

    for model in (Alert, DeliveryNoteItem, DeliveryNote, Movement, Batch):
        assert await count(model) == 0, model.__tablename__
    for model in (Item, Location, Customer, CustomerMachine, SystemSettings, User):
        assert await count(model) == 1, model.__tablename__
