"""
Database dependencies for FastAPI.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import async_session


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()