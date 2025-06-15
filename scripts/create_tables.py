#!/usr/bin/env python3
"""
Script to create database tables for the API Developer Portal.
"""
import asyncio
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# Import all models to register them with SQLModel
from app.models.user import User, EmailVerificationToken, PasswordResetToken
from app.models.api_key import APIKey, APIKeyUsage
from app.models.token import TokenBlacklist


async def create_tables():
    """Create all database tables."""
    # Use the same database URL as the running app
    database_url = "postgresql+asyncpg://devportal_user:dev_password_123@localhost:5433/devportal"
    
    print(f"Connecting to database: {database_url}")
    
    engine = create_async_engine(database_url, echo=True)
    
    try:
        async with engine.begin() as conn:
            print("Creating all tables...")
            await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ Database tables created successfully!")
        
        # Print created tables
        print("\n📊 Created tables:")
        for table_name in SQLModel.metadata.tables.keys():
            print(f"  - {table_name}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    finally:
        await engine.dispose()
    
    return True


async def create_test_tables():
    """Create tables for test database."""
    # Check if we're running in the test environment
    test_env = os.getenv("TEST_MODE", "false").lower() == "true"
    
    if test_env:
        # Running inside test container
        database_url = "postgresql+asyncpg://testuser:testpass@test-postgres:5432/testdb"
    else:
        # Running from outside container
        database_url = "postgresql+asyncpg://testuser:testpass@localhost:5434/testdb"
    
    print(f"Connecting to test database: {database_url}")
    
    engine = create_async_engine(database_url, echo=False)
    
    try:
        async with engine.begin() as conn:
            print("Creating test database tables...")
            await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ Test database tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating test tables: {e}")
        return False
    finally:
        await engine.dispose()
    
    return True


async def main():
    """Main function."""
    print("🗄️  API Developer Portal - Database Table Creation")
    print("=" * 55)
    
    # Check if we're in test mode
    test_env = os.getenv("TEST_MODE", "false").lower() == "true"
    
    if test_env:
        # Only create test tables when in test mode
        print("🧪 Test mode detected - creating test database tables only...")
        await create_test_tables()
    else:
        # Create production tables
        success = await create_tables()
        
        if success:
            print("\n🧪 Creating test database tables...")
            await create_test_tables()


if __name__ == "__main__":
    asyncio.run(main())