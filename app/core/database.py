"""
Database configuration and session management.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlmodel import SQLModel

from .config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


# Engine and session will be initialized later
engine = None
async_session = None


def init_database():
    """Initialize database engine and session."""
    global engine, async_session
    
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        future=True,
        pool_pre_ping=True,
        pool_recycle=300,
    )

    # Create async session factory
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
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


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


async def init_db():
    """Initialize database with tables and data."""
    await create_tables()
    
    # Create initial data if needed
    async with async_session() as session:
        # Import here to avoid circular imports
        from ..models.user import User, UserRole
        from ..core.security import get_password_hash
        
        # Check if admin user exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == settings.admin_username)
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            # Create admin user
            admin_user = User(
                username=settings.admin_username,
                email=settings.admin_email,
                hashed_password=get_password_hash(settings.admin_password),
                full_name="System Administrator",
                role=UserRole.admin,
                is_active=True,
                is_verified=True
            )
            session.add(admin_user)
            await session.commit()
            print(f"Created admin user: {settings.admin_username}")


async def close_db():
    """Close database connection."""
    if engine:
        await engine.dispose()