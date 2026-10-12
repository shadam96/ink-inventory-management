"""User management endpoints (admin-only)"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession
from app.core.security import get_password_hash
from app.models.location import Location
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserLocationAssignment, UserResponse, UserUpdate

router = APIRouter()


def _to_response(user: User) -> UserResponse:
    response = UserResponse.model_validate(user)
    response.location_ids = [loc.id for loc in user.locations]
    return response


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    db: DbSession,
    admin: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> PaginatedResponse[UserResponse]:
    """List all users. Admin-only - this surfaces every account in the
    system, including other admins."""
    query = select(User)

    if role:
        query = query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if search:
        like = f"%{search}%"
        query = query.where(
            (User.username.ilike(like))
            | (User.full_name.ilike(like))
            | (User.email.ilike(like))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(User.username.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=[_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: DbSession,
    admin: AdminUser,
) -> UserResponse:
    """Get a single user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="משתמש לא נמצא",  # User not found
        )

    return _to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: DbSession,
    admin: AdminUser,
) -> UserResponse:
    """Update a user's profile, role, active status, or password"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="משתמש לא נמצא",
        )

    update_data = user_data.model_dump(exclude_unset=True, exclude={"password"})

    if "username" in update_data and update_data["username"] != user.username:
        existing = await db.execute(
            select(User).where(User.username == update_data["username"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="שם משתמש כבר קיים",  # Username already exists
            )

    if "email" in update_data and update_data["email"] != user.email:
        existing = await db.execute(
            select(User).where(User.email == update_data["email"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="כתובת אימייל כבר קיימת",  # Email already exists
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)

    await db.commit()
    await db.refresh(user)

    return _to_response(user)


@router.put("/{user_id}/locations", response_model=UserResponse)
async def update_user_locations(
    user_id: UUID,
    assignment: UserLocationAssignment,
    db: DbSession,
    admin: AdminUser,
) -> UserResponse:
    """Replace a user's full set of assigned locations.

    An empty list clears all assignments (making the user unrestricted
    again, per the opt-in scoping design - see AccessScope in deps.py).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="משתמש לא נמצא",
        )

    if assignment.location_ids:
        loc_result = await db.execute(
            select(Location).where(Location.id.in_(assignment.location_ids))
        )
        found_locations = loc_result.scalars().all()
        found_ids = {loc.id for loc in found_locations}
        missing_ids = set(assignment.location_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"מיקומים לא נמצאו: {', '.join(str(i) for i in missing_ids)}",  # Locations not found
            )
        user.locations = list(found_locations)
    else:
        user.locations = []

    await db.commit()
    await db.refresh(user)

    return _to_response(user)
