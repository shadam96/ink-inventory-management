"""Create initial admin user.

Usage: ADMIN_PASSWORD=<password> python create_admin.py
"""
import asyncio
import os
import sys
from uuid import uuid4
from app.core.database import async_session_maker
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def create_admin():
    """Create admin user with password from ADMIN_PASSWORD env var."""
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        print("Error: ADMIN_PASSWORD env var is required")
        print("Usage: ADMIN_PASSWORD=<password> python create_admin.py")
        sys.exit(1)

    async with async_session_maker() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(">> Admin user already exists!")
            return

        admin = User(
            id=uuid4(),
            username="admin",
            email="admin@linoprint.com",
            full_name="Administrator",
            hashed_password=get_password_hash(password),
            role=UserRole.ADMIN,
            is_active=True
        )

        session.add(admin)
        await session.commit()

        print(">> Admin user created successfully!")
        print("  Username: admin")
        print("  Email: admin@linoprint.com")
        print("  Role: ADMIN")

if __name__ == "__main__":
    asyncio.run(create_admin())
