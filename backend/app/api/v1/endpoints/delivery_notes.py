"""Delivery Note endpoints"""
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, WarehouseUser, ManagerUser
from app.models.delivery_note import DeliveryNote, DeliveryNoteStatus
from app.services.document_service import DocumentService
from app.schemas.common import PaginatedResponse

router = APIRouter()


class DeliveryNoteItemInput(BaseModel):
    """Input for delivery note item"""
    batch_id: UUID
    quantity: Decimal = Field(..., gt=0)


class CreateDeliveryNoteRequest(BaseModel):
    """Request to create delivery note"""
    customer_id: UUID
    items: List[DeliveryNoteItemInput] = Field(..., min_length=1)
    is_consignment: bool = False
    notes: Optional[str] = None
    issue_date: Optional[date] = None


class DeliveryNoteResponse(BaseModel):
    """Delivery note response"""
    id: UUID
    delivery_note_number: str
    customer_id: UUID
    customer_name: Optional[str] = None
    status: str
    issue_date: Optional[date]
    delivery_date: Optional[date]
    is_consignment: bool
    notes: Optional[str]
    items_count: int
    total_quantity: float
    created_at: str
    created_by_name: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    """Request to update delivery note status"""
    status: DeliveryNoteStatus


@router.get("")
async def list_delivery_notes(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: Optional[UUID] = None,
    status_filter: Optional[DeliveryNoteStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """List delivery notes with filters"""
    query = (
        select(DeliveryNote)
        .options(
            selectinload(DeliveryNote.customer),
            selectinload(DeliveryNote.created_by_user),
            selectinload(DeliveryNote.items),
        )
        .order_by(DeliveryNote.created_at.desc())
    )
    
    if customer_id:
        query = query.where(DeliveryNote.customer_id == customer_id)
    
    if status_filter:
        query = query.where(DeliveryNote.status == status_filter)
    
    if start_date:
        query = query.where(DeliveryNote.issue_date >= start_date)
    
    if end_date:
        query = query.where(DeliveryNote.issue_date <= end_date)
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    notes = result.scalars().all()
    
    items = []
    for dn in notes:
        total_qty = sum(item.quantity for item in dn.items)
        items.append({
            "id": str(dn.id),
            "delivery_note_number": dn.delivery_note_number,
            "customer_id": str(dn.customer_id),
            "customer_name": dn.customer.name if dn.customer else None,
            "status": dn.status.value,
            "issue_date": dn.issue_date.isoformat() if dn.issue_date else None,
            "delivery_date": dn.delivery_date.isoformat() if dn.delivery_date else None,
            "is_consignment": dn.is_consignment,
            "notes": dn.notes,
            "items_count": len(dn.items),
            "total_quantity": float(total_qty),
            "created_at": dn.created_at.isoformat(),
            "created_by_name": dn.created_by_user.full_name if dn.created_by_user else None,
        })
    
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_delivery_note(
    request: CreateDeliveryNoteRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> dict:
    """Create a new delivery note"""
    service = DocumentService(db)
    
    try:
        items_data = [
            {"batch_id": item.batch_id, "quantity": item.quantity}
            for item in request.items
        ]
        
        dn = await service.create_delivery_note(
            customer_id=request.customer_id,
            items=items_data,
            user_id=current_user.id,
            is_consignment=request.is_consignment,
            notes=request.notes,
            issue_date=request.issue_date,
        )
        
        await db.commit()
        
        return {
            "id": str(dn.id),
            "delivery_note_number": dn.delivery_note_number,
            "status": dn.status.value,
            "items_count": len(request.items),
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{delivery_note_id}")
async def get_delivery_note(
    delivery_note_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Get delivery note details"""
    service = DocumentService(db)
    dn = await service.get_delivery_note_with_details(delivery_note_id)
    
    if not dn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="תעודת משלוח לא נמצאה",
        )
    
    items = []
    for item in dn.items:
        items.append({
            "id": str(item.id),
            "item_id": str(item.item_id),
            "item_sku": item.item.sku if item.item else None,
            "item_name": item.item.name if item.item else None,
            "batch_id": str(item.batch_id),
            "batch_number": item.batch.batch_number if item.batch else None,
            "expiration_date": item.batch.expiration_date.isoformat() if item.batch else None,
            "quantity": float(item.quantity),
            "unit": item.item.unit_of_measure if item.item else None,
        })
    
    return {
        "id": str(dn.id),
        "delivery_note_number": dn.delivery_note_number,
        "customer_id": str(dn.customer_id),
        "customer_name": dn.customer.name if dn.customer else None,
        "customer_address": dn.customer.address if dn.customer else None,
        "customer_contact": dn.customer.contact_person if dn.customer else None,
        "status": dn.status.value,
        "issue_date": dn.issue_date.isoformat() if dn.issue_date else None,
        "delivery_date": dn.delivery_date.isoformat() if dn.delivery_date else None,
        "is_consignment": dn.is_consignment,
        "notes": dn.notes,
        "items": items,
        "total_quantity": float(sum(i.quantity for i in dn.items)),
        "created_at": dn.created_at.isoformat(),
        "created_by_name": dn.created_by_user.full_name if dn.created_by_user else None,
    }


@router.put("/{delivery_note_id}/status")
async def update_delivery_note_status(
    delivery_note_id: UUID,
    request: UpdateStatusRequest,
    db: DbSession,
    current_user: WarehouseUser,
) -> dict:
    """Update delivery note status"""
    service = DocumentService(db)
    
    try:
        dn = await service.update_delivery_note_status(
            delivery_note_id=delivery_note_id,
            new_status=request.status,
        )
        await db.commit()
        
        return {
            "id": str(dn.id),
            "delivery_note_number": dn.delivery_note_number,
            "status": dn.status.value,
            "issue_date": dn.issue_date.isoformat() if dn.issue_date else None,
            "delivery_date": dn.delivery_date.isoformat() if dn.delivery_date else None,
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{delivery_note_id}/pdf")
async def get_delivery_note_pdf(
    delivery_note_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    """Generate and download delivery note PDF"""
    service = DocumentService(db)
    
    try:
        pdf_bytes = await service.generate_delivery_note_pdf(delivery_note_id)
        
        # Get DN number for filename
        dn = await service.get_delivery_note_with_details(delivery_note_id)
        filename = f"{dn.delivery_note_number}.pdf" if dn else "delivery_note.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
