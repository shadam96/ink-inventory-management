"""Create initial admin user"""
import asyncio
from uuid import uuid4
from app.core.database import async_session_maker
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def create_admin():
    """Create admin user"""
    async with async_session_maker() as session:
        # Check if admin exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(">> Admin user already exists!")
            print("\nLogin credentials:")
            print("  Username: admin")
            print("  Password: admin123")
            return
        
        # Create admin user
        admin = User(
            id=uuid4(),
            username="admin",
            email="admin@linoprint.com",
            full_name="Administrator",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        
        session.add(admin)
        await session.commit()
        
        print(">> Admin user created successfully!")
        print("\nLogin credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("  Email: admin@linoprint.com")
        print("  Role: ADMIN")

if __name__ == "__main__":
    asyncio.run(create_admin())
