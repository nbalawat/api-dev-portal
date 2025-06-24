"""
Demo endpoints for development and testing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.config import settings
from ..core.demo_users import create_demo_users, DEMO_USERS


router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/init-users")
async def initialize_demo_users(
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize demo users.
    """
    if settings.app_env == "production":
        raise HTTPException(
            status_code=403,
            detail="Demo users cannot be created in production environment"
        )
    
    await create_demo_users(db)
    
    return {
        "success": True,
        "message": "Demo users initialized successfully",
        "users": [
            {
                "email": user["email"],
                "password": user["password"],
                "role": user["role"]
            }
            for user in DEMO_USERS
        ]
    }


@router.get("/users")
async def get_demo_credentials():
    """
    Get demo user credentials (public endpoint for development).
    """
    if settings.app_env == "production":
        raise HTTPException(
            status_code=404,
            detail="This endpoint is not available in production"
        )
    
    return {
        "demo_users": [
            {
                "email": user["email"],
                "password": user["password"],
                "role": user["role"],
                "description": f"{user['role'].value.title()} user with {user['role'].value} permissions"
            }
            for user in DEMO_USERS
        ],
        "note": "These are demo credentials for testing purposes only"
    }