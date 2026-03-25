"""Database configuration and session management"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    poolclass=NullPool if settings.is_development else None,
    pool_pre_ping=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides database session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_default_users() -> None:
    """Create default admin and user accounts if they don't exist.

    Reads passwords from ADMIN_SEED_PASSWORD and USER_SEED_PASSWORD env vars.
    Skips seeding if env vars are not set or if users already exist.
    """
    import os
    from sqlalchemy import select
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash

    admin_password = os.environ.get("ADMIN_SEED_PASSWORD")
    user_password = os.environ.get("USER_SEED_PASSWORD")

    if not admin_password or not user_password:
        print(">> Skipping user seeding: set ADMIN_SEED_PASSWORD and USER_SEED_PASSWORD env vars to seed default users")
        return

    async with async_session_maker() as session:
        # Check if any users exist
        result = await session.execute(select(User).limit(1))
        if result.scalars().first() is not None:
            return  # Users already exist, skip seeding

        admin = User(
            username="admin",
            email="admin@linoprint.com",
            hashed_password=get_password_hash(admin_password),
            full_name="System Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        user = User(
            username="user",
            email="user@linoprint.com",
            hashed_password=get_password_hash(user_password),
            full_name="Default User",
            role=UserRole.VIEWER,
            is_active=True,
        )
        session.add_all([admin, user])
        await session.commit()
        print(">> Default users created (admin, user) with passwords from env vars")


async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()


