#!/usr/bin/env python3
"""
Script to generate test analytics data for the API developer portal.
This will create realistic API usage entries to test the analytics charts.
"""
import asyncio
import random
from datetime import datetime, timedelta
from uuid import uuid4
import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, init_database
from app.models.api_key import APIKeyUsage, APIKey
from app.models.user import User

# Test endpoints to simulate
TEST_ENDPOINTS = [
    "/api/users",
    "/api/auth/login", 
    "/api/auth/logout",
    "/api/data/fetch",
    "/api/files/upload",
    "/api/files/download",
    "/api/search",
    "/api/analytics/summary",
    "/api/api-keys",
    "/api/settings"
]

# HTTP methods and their weights
HTTP_METHODS = [
    ("GET", 0.6),
    ("POST", 0.25),
    ("PUT", 0.1),
    ("DELETE", 0.05)
]

# Status codes and their weights
STATUS_CODES = [
    (200, 0.75),
    (201, 0.1),
    (400, 0.05),
    (401, 0.03),
    (403, 0.02),
    (404, 0.03),
    (500, 0.02)
]

def weighted_choice(choices):
    """Choose a random item from weighted choices."""
    total = sum(weight for choice, weight in choices)
    r = random.uniform(0, total)
    upto = 0
    for choice, weight in choices:
        if upto + weight >= r:
            return choice
        upto += weight
    return choices[-1][0]  # fallback

def generate_realistic_response_time(status_code):
    """Generate realistic response times based on status code."""
    if status_code >= 500:
        # Server errors tend to be slower
        return random.uniform(1000, 5000)
    elif status_code >= 400:
        # Client errors are usually fast
        return random.uniform(50, 300)
    else:
        # Success responses vary by endpoint complexity
        return random.uniform(20, 1000)

def generate_ip_address():
    """Generate a random IP address."""
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"

def generate_user_agent():
    """Generate a random user agent."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "PostmanRuntime/7.28.4",
        "curl/7.68.0",
        "Python/3.9 requests/2.25.1"
    ]
    return random.choice(user_agents)

async def get_api_keys(session: AsyncSession):
    """Get all active API keys from the database."""
    from sqlalchemy import select
    result = await session.execute(
        select(APIKey).where(APIKey.status == "active")
    )
    return result.scalars().all()

async def generate_usage_data_for_timeframe(session: AsyncSession, api_keys: list, days_back: int = 7):
    """Generate usage data for the specified timeframe."""
    print(f"Generating usage data for {days_back} days...")
    
    usage_entries = []
    
    for day_offset in range(days_back):
        # Generate timestamp for this day
        base_date = datetime.utcnow() - timedelta(days=day_offset)
        
        # Generate more entries for recent days
        entries_per_day = random.randint(20, 100) if day_offset < 3 else random.randint(5, 30)
        
        for _ in range(entries_per_day):
            # Random time during the day
            timestamp = base_date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # Choose random API key
            api_key = random.choice(api_keys)
            
            # Choose endpoint and method
            endpoint = random.choice(TEST_ENDPOINTS)
            method = weighted_choice(HTTP_METHODS)
            status_code = weighted_choice(STATUS_CODES)
            
            # Generate response time
            response_time = generate_realistic_response_time(status_code)
            
            # Generate request/response sizes
            request_size = random.randint(100, 5000) if method in ["POST", "PUT"] else random.randint(0, 500)
            response_size = random.randint(200, 10000) if status_code < 400 else random.randint(50, 500)
            
            usage_entry = APIKeyUsage(
                api_key_id=api_key.id,
                timestamp=timestamp,
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time,
                ip_address=generate_ip_address(),
                user_agent=generate_user_agent(),
                request_size_bytes=request_size,
                response_size_bytes=response_size,
                error_code=f"HTTP_{status_code}" if status_code >= 400 else None,
                error_message="Client error" if 400 <= status_code < 500 else "Server error" if status_code >= 500 else None
            )
            
            usage_entries.append(usage_entry)
    
    # Bulk insert the usage entries
    session.add_all(usage_entries)
    await session.commit()
    
    print(f"Generated {len(usage_entries)} usage entries")
    return len(usage_entries)

async def clear_existing_usage_data(session: AsyncSession):
    """Clear existing usage data to start fresh."""
    from sqlalchemy import delete
    result = await session.execute(delete(APIKeyUsage))
    await session.commit()
    print(f"Cleared {result.rowcount} existing usage entries")

async def main():
    """Main function to generate test data."""
    print("🚀 Starting analytics test data generation...")
    
    # Initialize database
    init_database()
    
    # Get database session
    async for session in get_db():
        try:
            # Get all API keys
            api_keys = await get_api_keys(session)
            
            if not api_keys:
                print("❌ No API keys found! Please create at least one API key first.")
                print("   You can do this through the dashboard UI or directly in the database.")
                return
            
            print(f"📊 Found {len(api_keys)} API key(s) to generate data for:")
            for key in api_keys:
                print(f"   - {key.name} ({key.key_id})")
            
            # Ask user if they want to clear existing data
            response = input("\n🗑️  Clear existing usage data? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                await clear_existing_usage_data(session)
            
            # Generate data for the last 7 days
            total_entries = await generate_usage_data_for_timeframe(session, api_keys, days_back=7)
            
            print(f"\n✅ Successfully generated {total_entries} usage entries!")
            print("📈 You can now check the analytics charts in your dashboard.")
            
        except Exception as e:
            print(f"❌ Error generating test data: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            break

if __name__ == "__main__":
    asyncio.run(main())