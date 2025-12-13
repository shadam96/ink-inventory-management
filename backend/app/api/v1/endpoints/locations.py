"""Location endpoints"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, ManagerUser
from app.models.location import Location
from app.models.batch import BatchStatus
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate
from app.schemas.common import PaginatedResponse, MessageResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[LocationResponse])
async def list_locations(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse: Optional[str] = None,
    is_active: Optional[bool] = True,
) -> PaginatedResponse[LocationResponse]:
    """List all locations"""
    query = select(Location).options(selectinload(Location.batches))
    
    if warehouse:
        query = query.where(Location.warehouse.ilike(f"%{warehouse}%"))
    
    if is_active is not None:
        query = query.where(Location.is_active == is_active)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    locations = result.scalars().all()
    
    # Convert to response
    location_responses = []
    for location in locations:
        response = LocationResponse.model_validate(location)
        response.batches_count = len(location.batches)
        response.active_batches_count = len([
            b for b in location.batches if b.status == BatchStatus.ACTIVE
        ])
        location_responses.append(response)
    
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return PaginatedResponse(
        items=location_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_data: LocationCreate,
    db: DbSession,
    current_user: ManagerUser,
) -> LocationResponse:
    """Create a new storage location"""
    # Generate location code if not provided
    location_code = location_data.location_code or Location.generate_location_code(
        location_data.warehouse,
        location_data.shelf,
        location_data.position,
    )
    
    # Check if location code exists
    result = await db.execute(
        select(Location).where(Location.location_code == location_code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"קוד מיקום {location_code} כבר קיים",  # Location code already exists
        )
    
    location = Location(
        warehouse=location_data.warehouse,
        shelf=location_data.shelf,
        position=location_data.position,
        location_code=location_code,
        description=location_data.description,
    )
    
    db.add(location)
    await db.commit()
    await db.refresh(location)
    
    response = LocationResponse.model_validate(location)
    response.batches_count = 0
    response.active_batches_count = 0
    
    return response


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> LocationResponse:
    """Get location by ID"""
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.batches))
        .where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="מיקום לא נמצא",
        )
    
    response = LocationResponse.model_validate(location)
    response.batches_count = len(location.batches)
    response.active_batches_count = len([
        b for b in location.batches if b.status == BatchStatus.ACTIVE
    ])
    
    return response


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    location_data: LocationUpdate,
    db: DbSession,
    current_user: ManagerUser,
) -> LocationResponse:
    """Update a location"""
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.batches))
        .where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="מיקום לא נמצא",
        )
    
    # Update fields
    update_data = location_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)
    
    await db.commit()
    await db.refresh(location)
    
    response = LocationResponse.model_validate(location)
    response.batches_count = len(location.batches)
    response.active_batches_count = len([
        b for b in location.batches if b.status == BatchStatus.ACTIVE
    ])
    
    return response


@router.delete("/{location_id}", response_model=MessageResponse)
async def delete_location(
    location_id: UUID,
    db: DbSession,
    current_user: ManagerUser,
) -> MessageResponse:
    """Delete a location (only if no batches assigned)"""
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.batches))
        .where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="מיקום לא נמצא",
        )
    
    if location.batches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"לא ניתן למחוק מיקום עם {len(location.batches)} אצוות",
        )
    
    await db.delete(location)
    await db.commit()
    
    return MessageResponse(
        message=f"מיקום {location.location_code} נמחק בהצלחה",
        success=True,
    )


