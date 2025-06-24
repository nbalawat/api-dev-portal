"""
Demo users initialization for development and testing.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User, UserRole
from ..core.security import get_password_hash


DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin123",
        "full_name": "Admin User",
        "role": UserRole.admin,
        "is_active": True,
        "is_verified": True
    },
    {
        "username": "developer",
        "email": "developer@example.com",
        "password": "dev123",
        "full_name": "Developer User",
        "role": UserRole.developer,
        "is_active": True,
        "is_verified": True
    },
    {
        "username": "viewer",
        "email": "viewer@example.com",
        "password": "view123",
        "full_name": "Viewer User",
        "role": UserRole.viewer,
        "is_active": True,
        "is_verified": True
    }
]


async def create_demo_users(session: AsyncSession) -> None:
    """
    Create demo users if they don't exist.
    
    Args:
        session: Database session
    """
    for user_data in DEMO_USERS:
        # Check if user exists
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            # Create new user
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=user_data["is_active"],
                is_verified=user_data["is_verified"]
            )
            session.add(user)
            print(f"Created demo user: {user_data['email']}")
        else:
            # Update password to ensure it matches
            existing_user.hashed_password = get_password_hash(user_data["password"])
            existing_user.is_active = True
            existing_user.is_verified = True
            print(f"Updated demo user: {user_data['email']}")
    
    await session.commit()