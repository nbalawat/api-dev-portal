#!/usr/bin/env python3
"""
Debug script to isolate the exact cause of the 500 error.
"""
import asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://testuser:testpass@test-postgres:5432/testdb"

async def debug_database_issue():
    """Debug the exact database issue causing 500 errors."""
    
    # Test 1: Direct database connection
    print("🔍 Testing direct database connection...")
    try:
        engine = create_async_engine(TEST_DATABASE_URL, echo=True)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Direct database connection works")
        await engine.dispose()
    except Exception as e:
        print(f"❌ Direct database connection failed: {e}")
        return

    # Test 2: Test creating a user directly via database
    print("\n🔍 Testing direct user creation...")
    try:
        engine = create_async_engine(TEST_DATABASE_URL)
        SessionLocal = sessionmaker(engine, class_=AsyncSession)
        
        async with SessionLocal() as session:
            # Clear any existing data
            await session.execute(text("DELETE FROM users"))
            await session.commit()
            
            # Try to create a user directly
            user_sql = """
            INSERT INTO users (id, username, email, full_name, hashed_password, role, is_active, email_verified)
            VALUES (gen_random_uuid(), 'testuser', 'test@example.com', 'Test User', 'hashed_password', 'developer', true, false)
            """
            await session.execute(text(user_sql))
            await session.commit()
            print("✅ Direct user creation works")
            
        await engine.dispose()
    except Exception as e:
        print(f"❌ Direct user creation failed: {e}")
        return

    # Test 3: Test the API endpoint with debug
    print("\n🔍 Testing API endpoint...")
    try:
        async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
            user_data = {
                "username": "apitest",
                "email": "apitest@example.com", 
                "full_name": "API Test",
                "password": "testpass123",
                "confirm_password": "testpass123",
                "role": "developer"
            }
            
            response = await client.post("/auth/register", json=user_data)
            print(f"API Response: {response.status_code}")
            if response.status_code != 200:
                print(f"Error response: {response.text}")
            else:
                print("✅ API endpoint works")
                
    except Exception as e:
        print(f"❌ API endpoint failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_database_issue())