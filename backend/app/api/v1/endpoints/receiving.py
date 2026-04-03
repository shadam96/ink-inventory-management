"""Goods Receipt endpoints"""
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession, WarehouseUser
from app.services.receiving_service import ReceivingService
from app.schemas.batch import BatchResponse
from app.schemas.common import MessageResponse

router = APIRouter()


class GoodsReceiptItem(BaseModel):
    """Single item in goods receipt"""
    item_id: UUID
    quantity: Decimal = Field(..., gt=0)
    expiration_date: date
    batch_number: Optional[str] = None
    supplier_batch_number: Optional[str] = None
    location_id: Optional[UUID] = None
    notes: Optional[str] = None


class GoodsReceiptRequest(BaseModel):
    """Request to receive goods"""
    items: List[GoodsReceiptItem] = Field(..., min_length=1)


class GoodsReceiptResponse(BaseModel):
    """Response from goods receipt"""
    grn_number: str
    batches_created: int
    total_quantity: Decimal
    items: List[dict]
    warnings: List[dict] = []


class SingleReceiptRequest(BaseModel):
    """Request to receive a single item"""
    item_id: UUID
    quantity: Decimal = Field(..., gt=0)
    expiration_date: date
    batch_number: Optional[str] = None
    supplier_batch_number: Optional[str] = None
    location_id: Optional[UUID] = None
    notes: Optional[str] = None


class SingleReceiptResponse(BaseModel):
    """Response from single item receipt"""
    grn_number: str
    batch_number: str
    batch_id: UUID
    item_id: UUID
    quantity: Decimal
    expiration_date: date
    location_id: Optional[UUID]
    warning: Optional[dict] = None


@router.post("/receive", response_model=SingleReceiptResponse)
async def receive_single_item(
    receipt: SingleReceiptRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> SingleReceiptResponse:
    """
    Receive a single item into inventory.
    Creates a new batch and records the receipt movement.
    """
    service = ReceivingService(db)
    
    try:
        batch, movement, grn_number = await service.receive_goods(
            item_id=receipt.item_id,
            quantity=receipt.quantity,
            expiration_date=receipt.expiration_date,
            user_id=current_user.id,
            batch_number=receipt.batch_number,
            supplier_batch_number=receipt.supplier_batch_number,
            location_id=receipt.location_id,
            notes=receipt.notes,
        )
        
        await db.commit()
        
        # Check for expiration warning
        warning = service.validate_expiration_warning(receipt.expiration_date)
        
        return SingleReceiptResponse(
            grn_number=grn_number,
            batch_number=batch.batch_number,
            batch_id=batch.id,
            item_id=batch.item_id,
            quantity=batch.quantity_received,
            expiration_date=batch.expiration_date,
            location_id=batch.location_id,
            warning=warning,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/receive-multiple", response_model=GoodsReceiptResponse)
async def receive_multiple_items(
    request: GoodsReceiptRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> GoodsReceiptResponse:
    """
    Receive multiple items in a single GRN (Goods Receipt Note).
    """
    service = ReceivingService(db)
    
    try:
        receipts_data = [
            {
                "item_id": item.item_id,
                "quantity": item.quantity,
                "expiration_date": item.expiration_date,
                "batch_number": item.batch_number,
                "supplier_batch_number": item.supplier_batch_number,
                "location_id": item.location_id,
                "notes": item.notes,
            }
            for item in request.items
        ]
        
        batches, movements, grn_number = await service.receive_multiple(
            receipts=receipts_data,
            user_id=current_user.id,
        )
        
        await db.commit()
        
        # Collect warnings
        warnings = []
        items_response = []
        
        for i, batch in enumerate(batches):
            warning = service.validate_expiration_warning(batch.expiration_date)
            if warning:
                warning["batch_number"] = batch.batch_number
                warnings.append(warning)
            
            items_response.append({
                "batch_id": str(batch.id),
                "batch_number": batch.batch_number,
                "item_id": str(batch.item_id),
                "quantity": float(batch.quantity_received),
                "expiration_date": batch.expiration_date.isoformat(),
            })
        
        total_quantity = sum(b.quantity_received for b in batches)
        
        return GoodsReceiptResponse(
            grn_number=grn_number,
            batches_created=len(batches),
            total_quantity=total_quantity,
            items=items_response,
            warnings=warnings,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


class BarcodeRequest(BaseModel):
    """Request body for barcode validation"""
    barcode: str


@router.post("/validate-barcode")
async def validate_barcode(
    request: BarcodeRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> dict:
    """
    Validate a scanned barcode/SKU and return item info.
    Searches barcode column, then SKU by exact match.
    If no exact match, tries each space-separated token from the scanned
    string (handles structured QR codes that embed the SKU among other data).
    """
    from sqlalchemy import func, literal, select, or_
    from app.models.item import Item

    scanned = request.barcode.strip()

    # 1. Try exact match on barcode or SKU
    result = await db.execute(
        select(Item).where(
            or_(
                Item.barcode == scanned,
                Item.sku == scanned,
            )
        )
    )
    item = result.scalar_one_or_none()

    # 2. If no exact match, find any item whose SKU or barcode appears
    #    as a substring in the scanned string. Prioritise longer matches
    #    to avoid false positives (e.g. SKU "10" matching quantity "10").
    if not item:
        result = await db.execute(
            select(Item).where(
                or_(
                    literal(scanned).contains(Item.sku),
                    literal(scanned).contains(Item.barcode),
                )
            ).order_by(func.length(Item.sku).desc())
        )
        item = result.scalars().first()

    if not item:
        return {
            "valid": False,
            "item": None
        }

    return {
        "valid": True,
        "item": {
            "id": str(item.id),
            "sku": item.sku,
            "barcode": item.barcode,
            "name": item.name,
            "supplier": item.supplier,
            "unit_of_measure": item.unit_of_measure,
            "cost_price": float(item.cost_price),
        }
    }


@router.get("/generate-batch-number")
async def generate_batch_number(
    db: DbSession,
    current_user: WarehouseUser,
    prefix: str = "GR",
) -> dict:
    """Generate a new batch number"""
    service = ReceivingService(db)
    batch_number = await service.generate_batch_number(prefix)
    
    return {"batch_number": batch_number}

