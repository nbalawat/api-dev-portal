"""
Database dependencies for FastAPI.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from ..core import database


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    if database.async_session is None:
        raise HTTPException(
            status_code=503,
            detail="Database not initialized. Please wait for the service to fully start."
        )
    
    async with database.async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()