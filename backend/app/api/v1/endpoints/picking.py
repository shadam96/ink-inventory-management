"""Picking and dispatch endpoints with FEFO support"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DbSession, PickingUser, WarehouseUser
from app.services.fefo_engine import FEFOEngine
from app.services.inventory_service import InventoryService
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem
from app.models.movement import Movement, MovementType
from app.models.user import UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


class PickingSuggestionRequest(BaseModel):
    """Request for picking suggestions"""
    item_id: UUID
    quantity_needed: Decimal = Field(default=Decimal("0"), ge=0)


class BatchPickRequest(BaseModel):
    """Request to pick from a specific batch"""
    batch_id: UUID
    quantity: Decimal = Field(..., gt=0)


class DispatchItem(BaseModel):
    """Item in a dispatch request"""
    batch_id: UUID
    quantity: Decimal = Field(..., gt=0)


class DispatchRequest(BaseModel):
    """Request to create a dispatch"""
    items: List[DispatchItem] = Field(..., min_length=1)
    customer_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class ConsumeRequest(BaseModel):
    """Request for customer consumption — pick specific batch"""
    batch_id: UUID
    quantity: Decimal = Field(..., gt=0)
    notes: Optional[str] = None


class DispatchResponse(BaseModel):
    """Response from dispatch creation"""
    success: bool
    reference_number: str
    items_dispatched: int
    total_quantity: Decimal
    movements: List[dict]


class DispatchDocumentRequest(BaseModel):
    """Request for generating/sending a document for a dispatch."""

    document_type: Literal["pick_note", "delivery_note"]
    action: Literal["print", "email"]


class DispatchDocumentResponse(BaseModel):
    """Stub response for dispatch document generation."""

    success: bool
    document_type: str
    action: str
    reference_number: str
    message: str


@router.post("/suggest-batches")
async def suggest_batches_for_picking(
    request: PickingSuggestionRequest,
    db: DbSession,
    current_user: PickingUser,
) -> dict:
    """
    Get batch suggestions for picking using FEFO, FIFO, and LIFO strategies.

    Never returns 400 for insufficient quantity — instead ``can_fulfill``
    is ``false`` and the available batches are still returned so the UI
    can show what exists.
    """
    fefo = FEFOEngine(db)

    total_available = await fefo.get_total_available(request.item_id)
    can_fulfill = total_available >= request.quantity_needed if request.quantity_needed > 0 else True

    fefo_suggestions = await fefo.suggest_batches_for_picking(
        item_id=request.item_id,
        quantity_needed=request.quantity_needed,
        strategy="fefo",
    )
    fifo_suggestions = await fefo.suggest_batches_for_picking(
        item_id=request.item_id,
        quantity_needed=request.quantity_needed,
        strategy="fifo",
    )
    lifo_suggestions = await fefo.suggest_batches_for_picking(
        item_id=request.item_id,
        quantity_needed=request.quantity_needed,
        strategy="lifo",
    )

    return {
        "item_id": str(request.item_id),
        "quantity_needed": float(request.quantity_needed),
        "total_available": float(total_available),
        "can_fulfill": can_fulfill,
        "suggestions": [s.to_dict() for s in fefo_suggestions],
        "fifo_suggestions": [s.to_dict() for s in fifo_suggestions],
        "lifo_suggestions": [s.to_dict() for s in lifo_suggestions],
    }


@router.post("/validate-pick")
async def validate_pick(
    request: BatchPickRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> dict:
    """
    Validate a picking operation before execution.
    
    Checks batch availability, expiration, and FEFO compliance.
    Returns warnings if picking from a batch with earlier-expiring alternatives.
    """
    fefo = FEFOEngine(db)
    
    validation = await fefo.validate_picking(
        batch_id=request.batch_id,
        quantity=request.quantity,
    )
    
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "בחירה לא תקינה",  # Invalid pick
                "errors": validation.errors,
            },
        )
    
    return validation.to_dict()


@router.post("/execute-pick")
async def execute_pick(
    request: BatchPickRequest,
    db: DbSession,
    current_user: WarehouseUser,
    reference_number: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Execute a single pick operation from a batch.
    Records the movement and updates batch quantity.
    """
    fefo = FEFOEngine(db)
    inventory = InventoryService(db)
    
    # Validate first
    validation = await fefo.validate_picking(
        batch_id=request.batch_id,
        quantity=request.quantity,
    )
    
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "בחירה לא תקינה",
                "errors": validation.errors,
            },
        )
    
    try:
        movement = await inventory.record_movement(
            batch_id=request.batch_id,
            movement_type=MovementType.DISPATCH,
            quantity=request.quantity,
            user_id=current_user.id,
            reference_number=reference_number,
            notes=notes,
        )
        
        await db.commit()
        
        return {
            "success": True,
            "movement_id": str(movement.id),
            "batch_id": str(request.batch_id),
            "quantity": float(request.quantity),
            "quantity_remaining": float(movement.quantity_after),
            "warnings": validation.warnings,
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/dispatch", response_model=DispatchResponse)
async def create_dispatch(
    request: DispatchRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> DispatchResponse:
    """
    Create a dispatch with multiple items.
    
    Validates all picks using FEFO, then executes them atomically.
    """
    fefo = FEFOEngine(db)
    inventory = InventoryService(db)
    
    # Validate all picks first
    all_warnings = []
    for item in request.items:
        validation = await fefo.validate_picking(
            batch_id=item.batch_id,
            quantity=item.quantity,
        )
        
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"שגיאה באצווה {item.batch_id}",
                    "errors": validation.errors,
                },
            )
        
        all_warnings.extend(validation.warnings)
    
    # Generate reference number if not provided
    ref_number = request.reference_number
    if not ref_number:
        from app.services.receiving_service import ReceivingService
        receiving = ReceivingService(db)
        ref_number = await receiving.generate_batch_number(prefix="DSP")
    
    # Execute all picks
    movements = []
    total_quantity = Decimal("0")
    
    try:
        for item in request.items:
            movement = await inventory.record_movement(
                batch_id=item.batch_id,
                movement_type=MovementType.DISPATCH,
                quantity=item.quantity,
                user_id=current_user.id,
                reference_number=ref_number,
                notes=request.notes,
            )
            
            movements.append({
                "movement_id": str(movement.id),
                "batch_id": str(item.batch_id),
                "quantity": float(item.quantity),
                "quantity_remaining": float(movement.quantity_after),
            })
            total_quantity += item.quantity
        
        await db.commit()
        
        return DispatchResponse(
            success=True,
            reference_number=ref_number,
            items_dispatched=len(movements),
            total_quantity=total_quantity,
            movements=movements,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/dispatches/{reference_number}/document",
    response_model=DispatchDocumentResponse,
)
async def generate_dispatch_document(
    reference_number: str,
    request: DispatchDocumentRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> DispatchDocumentResponse:
    """
    Generate or send a document for a dispatch (pick note or delivery note).

    NOTE: this endpoint is a stub. The actual document templates and
    rendering are not yet implemented. It returns ``success=False`` with an
    honest "not implemented" message so the UI does not mislead operators
    into believing a document was actually produced.
    """
    # Verify the reference corresponds to a real dispatch so we don't
    # silently accept arbitrary strings.
    exists = await db.execute(
        select(Movement.id)
        .where(Movement.reference_number == reference_number)
        .limit(1)
    )
    if exists.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"לא נמצא ליקוט עם מספר אסמכתא {reference_number}",
        )

    logger.info(
        "Document request (stub, not implemented): ref=%s type=%s action=%s user=%s",
        reference_number,
        request.document_type,
        request.action,
        current_user.id,
    )

    type_label = "תעודת ליקוט" if request.document_type == "pick_note" else "תעודת משלוח"
    message = f"{type_label}: הפקת המסמך טרם הוטמעה במערכת"

    return DispatchDocumentResponse(
        success=False,
        document_type=request.document_type,
        action=request.action,
        reference_number=reference_number,
        message=message,
    )


@router.post("/consume")
async def consume_item(
    request: ConsumeRequest,
    db: DbSession,
    current_user: PickingUser,
) -> dict:
    """
    Record customer consumption of an item.

    Any picking-authorized user can call this endpoint.  When the caller
    has the CUSTOMER role, their linked customer_id is recorded
    automatically, and the batch must belong to stock already dispatched
    to that customer (i.e. it appears on one of their delivery notes) -
    a customer cannot consume from another customer's stock.
    """
    if current_user.role == UserRole.CUSTOMER:
        allocated = await db.execute(
            select(DeliveryNoteItem.id)
            .join(DeliveryNote, DeliveryNoteItem.delivery_note_id == DeliveryNote.id)
            .where(DeliveryNoteItem.batch_id == request.batch_id)
            .where(DeliveryNote.customer_id == current_user.customer_id)
            .limit(1)
        )
        if allocated.first() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="המנה אינה שייכת ללקוח זה",  # This batch does not belong to this customer
            )

    fefo = FEFOEngine(db)
    inventory = InventoryService(db)

    validation = await fefo.validate_picking(
        batch_id=request.batch_id,
        quantity=request.quantity,
    )

    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "בחירה לא תקינה",
                "errors": validation.errors,
            },
        )

    try:
        # Build notes with customer context
        notes_parts = []
        if current_user.role == UserRole.CUSTOMER and current_user.customer_id:
            notes_parts.append(f"customer:{current_user.customer_id}")
        if request.notes:
            notes_parts.append(request.notes)

        from app.services.receiving_service import ReceivingService
        receiving = ReceivingService(db)
        ref_number = await receiving.generate_batch_number(prefix="CON")

        movement = await inventory.record_movement(
            batch_id=request.batch_id,
            movement_type=MovementType.CONSUMPTION,
            quantity=request.quantity,
            user_id=current_user.id,
            reference_number=ref_number,
            notes=" | ".join(notes_parts) if notes_parts else None,
        )

        await db.commit()

        return {
            "success": True,
            "movement_id": str(movement.id),
            "batch_id": str(request.batch_id),
            "quantity": float(request.quantity),
            "quantity_remaining": float(movement.quantity_after),
            "reference_number": ref_number,
            "warnings": validation.warnings,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/expiration-summary/{item_id}")
async def get_expiration_summary(
    item_id: UUID,
    db: DbSession,
    current_user: WarehouseUser,
) -> dict:
    """
    Get expiration breakdown for an item's inventory.
    Shows quantities by expiration risk level.
    """
    fefo = FEFOEngine(db)
    summary = await fefo.get_expiration_summary(item_id)
    
    # Convert Decimals to floats for JSON serialization
    return {
        "item_id": str(item_id),
        "total_quantity": float(summary["total_quantity"]),
        "total_batches": summary["total_batches"],
        "breakdown": {
            "expired": {
                "quantity": float(summary["expired"]["quantity"]),
                "batches": summary["expired"]["batches"],
            },
            "critical_30_days": {
                "quantity": float(summary["critical"]["quantity"]),
                "batches": summary["critical"]["batches"],
            },
            "warning_60_days": {
                "quantity": float(summary["warning"]["quantity"]),
                "batches": summary["warning"]["batches"],
            },
            "caution_90_days": {
                "quantity": float(summary["caution"]["quantity"]),
                "batches": summary["caution"]["batches"],
            },
            "safe": {
                "quantity": float(summary["safe"]["quantity"]),
                "batches": summary["safe"]["batches"],
            },
        }
    }

