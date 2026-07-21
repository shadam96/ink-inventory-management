"""Inventory view endpoint — aggregated current stock"""
from datetime import date
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem
from app.models.user import UserRole
from app.schemas.common import BaseSchema, PaginatedResponse

router = APIRouter()


class InventoryRowResponse(BaseSchema):
    """Single row in the inventory view: one (SKU, batch_number) combo."""

    item_id: UUID
    sku: str
    name: str
    description: Optional[str] = None
    batch_number: str
    quantity_available: Decimal
    unit_of_measure: str
    cost_price: Decimal
    currency: str
    supplier: str
    expiration_date: date
    receipt_dates: List[date]
    status: str


class InventoryTotalCostResponse(BaseSchema):
    """Total cost of inventory broken down by currency."""

    totals: dict[str, Decimal]


@router.get("", response_model=PaginatedResponse[InventoryRowResponse])
async def list_inventory(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    sort_by: Optional[
        Literal[
            "sku",
            "name",
            "batch_number",
            "quantity_available",
            "expiration_date",
            "receipt_date",
            "cost_price",
            "supplier",
            "status",
        ]
    ] = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> PaginatedResponse[InventoryRowResponse]:
    """
    Aggregated inventory view.

    * **Staff / admin**: full warehouse stock.
    * **Customer**: only batches dispatched to them via delivery notes.

    Rows are grouped by (item, batch_number).  Multiple receipts of the
    same SKU + batch merge into one row; individual receipt dates are
    returned in the ``receipt_dates`` array.
    """

    is_customer = current_user.role == UserRole.CUSTOMER

    # ------------------------------------------------------------------
    # Customer path — derive from delivery‑note items
    # ------------------------------------------------------------------
    if is_customer and current_user.customer_id:
        return await _customer_inventory(
            db,
            customer_id=current_user.customer_id,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    # ------------------------------------------------------------------
    # Staff / admin path — warehouse inventory from batches table
    # ------------------------------------------------------------------
    base = (
        select(Batch)
        .join(Item, Batch.item_id == Item.id)
        .options(selectinload(Batch.item))
        .where(Batch.status == BatchStatus.ACTIVE)
        .where(Batch.quantity_available > 0)
    )

    if search:
        like = f"%{search}%"
        base = base.where(
            (Item.sku.ilike(like))
            | (Item.name.ilike(like))
            | (Batch.batch_number.ilike(like))
            | (Item.supplier.ilike(like))
        )

    # Sorting
    sort_col = _resolve_sort_column(sort_by)
    if sort_col is not None:
        base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    else:
        base = base.order_by(Item.sku.asc(), Batch.expiration_date.asc())

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    rows = (
        await db.execute(base.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    # Build response — group receipt_dates per (item_id, batch_number)
    items_out: list[InventoryRowResponse] = []
    for batch in rows:
        item = batch.item
        # Determine display status
        if batch.expiration_date < date.today():
            display_status = "expired"
        else:
            display_status = batch.status.value

        items_out.append(
            InventoryRowResponse(
                item_id=item.id,
                sku=item.sku,
                name=item.name,
                description=item.description,
                batch_number=batch.batch_number,
                quantity_available=batch.quantity_available,
                unit_of_measure=item.unit_of_measure,
                cost_price=item.cost_price,
                currency=item.currency,
                supplier=item.supplier,
                expiration_date=batch.expiration_date,
                receipt_dates=[batch.receipt_date],
                status=display_status,
            )
        )

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items_out,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/total-cost", response_model=InventoryTotalCostResponse)
async def get_inventory_total_cost(
    db: DbSession,
    current_user: CurrentUser,
    search: Optional[str] = None,
) -> InventoryTotalCostResponse:
    """
    Total cost of active inventory (quantity_available * cost_price),
    grouped by currency.  Respects the same search filter as the list view.
    """
    is_customer = current_user.role == UserRole.CUSTOMER

    if is_customer and current_user.customer_id:
        # Dedupe by batch_id first — the same Batch may be referenced by
        # multiple DeliveryNoteItem rows for the same customer (e.g. a split
        # delivery or a correction). Without DISTINCT ON, the sum counts
        # `quantity_available` once per DeliveryNoteItem, inflating the total.
        dedup = (
            select(
                Batch.id.label("batch_id"),
                Batch.quantity_available,
                Item.cost_price,
                Item.currency,
                Item.sku,
                Item.name,
                Item.supplier,
                Batch.batch_number,
            )
            .select_from(DeliveryNoteItem)
            .join(DeliveryNote, DeliveryNoteItem.delivery_note_id == DeliveryNote.id)
            .join(Batch, DeliveryNoteItem.batch_id == Batch.id)
            .join(Item, DeliveryNoteItem.item_id == Item.id)
            .where(DeliveryNote.customer_id == current_user.customer_id)
            .where(Batch.status == BatchStatus.ACTIVE)
            .where(Batch.quantity_available > 0)
        )
        if search:
            like = f"%{search}%"
            dedup = dedup.where(
                (Item.sku.ilike(like))
                | (Item.name.ilike(like))
                | (Batch.batch_number.ilike(like))
                | (Item.supplier.ilike(like))
            )
        dedup_sub = dedup.distinct(Batch.id).subquery()

        stmt = (
            select(
                dedup_sub.c.currency,
                func.coalesce(
                    func.sum(dedup_sub.c.quantity_available * dedup_sub.c.cost_price),
                    0,
                ),
            )
            .group_by(dedup_sub.c.currency)
        )
    else:
        stmt = (
            select(
                Item.currency,
                func.coalesce(
                    func.sum(Batch.quantity_available * Item.cost_price),
                    0,
                ),
            )
            .select_from(Batch)
            .join(Item, Batch.item_id == Item.id)
            .where(Batch.status == BatchStatus.ACTIVE)
            .where(Batch.quantity_available > 0)
            .group_by(Item.currency)
        )

        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                (Item.sku.ilike(like))
                | (Item.name.ilike(like))
                | (Batch.batch_number.ilike(like))
                | (Item.supplier.ilike(like))
            )

    rows = (await db.execute(stmt)).all()
    totals = {currency: Decimal(value) for currency, value in rows}
    return InventoryTotalCostResponse(totals=totals)


# ------------------------------------------------------------------
# Customer inventory helper
# ------------------------------------------------------------------

async def _customer_inventory(
    db,
    customer_id: UUID,
    page: int,
    page_size: int,
    search: Optional[str],
    sort_by: Optional[str],
    sort_order: str,
) -> PaginatedResponse[InventoryRowResponse]:
    """Build inventory rows from delivery-note items for a customer."""

    base = (
        select(DeliveryNoteItem)
        .join(DeliveryNote, DeliveryNoteItem.delivery_note_id == DeliveryNote.id)
        .join(Batch, DeliveryNoteItem.batch_id == Batch.id)
        .join(Item, DeliveryNoteItem.item_id == Item.id)
        .where(DeliveryNote.customer_id == customer_id)
        .where(Batch.status == BatchStatus.ACTIVE)
        .where(Batch.quantity_available > 0)
    )

    if search:
        like = f"%{search}%"
        base = base.where(
            (Item.sku.ilike(like))
            | (Item.name.ilike(like))
            | (Batch.batch_number.ilike(like))
            | (Item.supplier.ilike(like))
        )

    sort_col = _resolve_sort_column(sort_by)
    if sort_col is not None:
        base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    else:
        base = base.order_by(Item.sku.asc())

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (
        await db.execute(
            base.offset((page - 1) * page_size)
            .limit(page_size)
            .options(
                selectinload(DeliveryNoteItem.batch).selectinload(Batch.item),
            )
        )
    ).scalars().all()

    items_out: list[InventoryRowResponse] = []
    for dni in rows:
        batch = dni.batch
        item = batch.item
        display_status = "expired" if batch.expiration_date < date.today() else batch.status.value

        items_out.append(
            InventoryRowResponse(
                item_id=item.id,
                sku=item.sku,
                name=item.name,
                description=item.description,
                batch_number=batch.batch_number,
                quantity_available=batch.quantity_available,
                unit_of_measure=item.unit_of_measure,
                cost_price=item.cost_price,
                currency=item.currency,
                supplier=item.supplier,
                expiration_date=batch.expiration_date,
                receipt_dates=[batch.receipt_date],
                status=display_status,
            )
        )

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items_out, total=total, page=page, page_size=page_size, pages=pages,
    )


# ------------------------------------------------------------------
# Sorting helper
# ------------------------------------------------------------------

def _resolve_sort_column(sort_by: Optional[str]):
    """Map sort_by string to SQLAlchemy column."""
    if sort_by is None:
        return None
    mapping = {
        "sku": Item.sku,
        "name": Item.name,
        "batch_number": Batch.batch_number,
        "quantity_available": Batch.quantity_available,
        "expiration_date": Batch.expiration_date,
        "receipt_date": Batch.receipt_date,
        "cost_price": Item.cost_price,
        "supplier": Item.supplier,
        "status": Batch.status,
    }
    return mapping.get(sort_by)
