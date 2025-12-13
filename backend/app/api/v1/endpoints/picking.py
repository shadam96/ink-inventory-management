"""Picking and dispatch endpoints with FEFO support"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession, WarehouseUser
from app.services.fefo_engine import FEFOEngine
from app.services.inventory_service import InventoryService
from app.models.movement import MovementType

router = APIRouter()


class PickingSuggestionRequest(BaseModel):
    """Request for picking suggestions"""
    item_id: UUID
    quantity_needed: Decimal = Field(..., gt=0)


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
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class DispatchResponse(BaseModel):
    """Response from dispatch creation"""
    success: bool
    reference_number: str
    items_dispatched: int
    total_quantity: Decimal
    movements: List[dict]


@router.post("/suggest-batches")
async def suggest_batches_for_picking(
    request: PickingSuggestionRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> dict:
    """
    Get FEFO-sorted batch suggestions for picking.
    
    Returns batches ordered by expiration date (soonest first)
    with suggested quantities to pick from each.
    """
    fefo = FEFOEngine(db)
    
    # Check if we can fulfill the request
    total_available = await fefo.get_total_available(request.item_id)
    
    if total_available < request.quantity_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"כמות לא מספיקה במלאי. זמין: {total_available}, נדרש: {request.quantity_needed}",
        )
    
    suggestions = await fefo.suggest_batches_for_picking(
        item_id=request.item_id,
        quantity_needed=request.quantity_needed,
    )
    
    return {
        "item_id": str(request.item_id),
        "quantity_needed": float(request.quantity_needed),
        "total_available": float(total_available),
        "suggestions": [s.to_dict() for s in suggestions],
        "can_fulfill": True,
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

