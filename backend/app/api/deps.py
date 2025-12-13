"""API dependencies for authentication and authorization"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User, UserRole

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    token_data = verify_token(token, token_type="access")
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="טוקן לא תקין או פג תוקף",  # Invalid or expired token
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="משתמש לא נמצא",  # User not found
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="משתמש לא פעיל",  # User is inactive
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure user is active"""
    return current_user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory for role-based access control"""
    
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="אין לך הרשאה לפעולה זו",  # You don't have permission for this action
            )
        return current_user
    
    return role_checker


# Pre-defined role dependencies
RequireAdmin = Depends(require_roles(UserRole.ADMIN))
RequireManager = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
RequireWarehouse = Depends(
    require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.WAREHOUSE_WORKER)
)

# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, RequireAdmin]
ManagerUser = Annotated[User, RequireManager]
WarehouseUser = Annotated[User, RequireWarehouse]
DbSession = Annotated[AsyncSession, Depends(get_db)]


