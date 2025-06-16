#!/usr/bin/env python3
"""
Comprehensive traffic generator for testing analytics.
"""
import asyncio
import aiohttp
import random
import time
from datetime import datetime

# API Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "sk_PbPz0_WgKpNP0U3-1sjJCRpFcKKNuLpVgwcqQ_GwYnc"

# Endpoints that work with API key authentication
ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/profile", "weight": 20},
    {"method": "GET", "path": "/api/v1/api-key/info", "weight": 15},
    {"method": "GET", "path": "/api/v1/api-key/usage-stats", "weight": 10},
    {"method": "POST", "path": "/api/v1/test-endpoint", "weight": 5, "body": {"test": True, "data": "sample"}},
    {"method": "GET", "path": "/api/api-keys/", "weight": 8},
    {"method": "GET", "path": "/health", "weight": 2},
]

def weighted_choice(endpoints):
    """Choose endpoint based on weights."""
    total = sum(e["weight"] for e in endpoints)
    r = random.uniform(0, total)
    upto = 0
    for endpoint in endpoints:
        if upto + endpoint["weight"] >= r:
            return endpoint
        upto += endpoint["weight"]
    return endpoints[0]

async def make_request(session, endpoint):
    """Make a request to an endpoint."""
    url = f"{API_BASE_URL}{endpoint['path']}"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    
    try:
        start_time = time.time()
        
        if endpoint["method"] == "GET":
            async with session.get(url, headers=headers) as response:
                response_time = (time.time() - start_time) * 1000
                status = response.status
                text = await response.text()
        else:  # POST
            body = endpoint.get("body", {})
            async with session.post(url, headers=headers, json=body) as response:
                response_time = (time.time() - start_time) * 1000
                status = response.status
                text = await response.text()
        
        success = 200 <= status < 400
        if success:
            print(f"✅ {endpoint['method']} {endpoint['path']} -> {status} ({response_time:.1f}ms)")
        else:
            print(f"❌ {endpoint['method']} {endpoint['path']} -> {status} ({response_time:.1f}ms)")
            
        return success
        
    except Exception as e:
        print(f"❌ {endpoint['method']} {endpoint['path']} -> Error: {e}")
        return False

async def generate_burst_traffic(requests_count=50):
    """Generate a burst of traffic."""
    print(f"🚀 Generating {requests_count} requests...")
    
    success_count = 0
    
    async with aiohttp.ClientSession() as session:
        for i in range(requests_count):
            endpoint = weighted_choice(ENDPOINTS)
            success = await make_request(session, endpoint)
            
            if success:
                success_count += 1
            
            # Random delay between requests
            await asyncio.sleep(random.uniform(0.1, 1.0))
            
            # Progress update
            if (i + 1) % 10 == 0:
                print(f"📊 Progress: {i + 1}/{requests_count} requests ({success_count} successful)")
    
    print(f"\n🎉 Completed! {success_count}/{requests_count} requests successful")
    return success_count

async def generate_continuous_traffic(duration_minutes=10):
    """Generate continuous traffic for specified duration."""
    print(f"⏰ Generating continuous traffic for {duration_minutes} minutes...")
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    request_count = 0
    success_count = 0
    
    async with aiohttp.ClientSession() as session:
        while time.time() < end_time:
            endpoint = weighted_choice(ENDPOINTS)
            success = await make_request(session, endpoint)
            
            request_count += 1
            if success:
                success_count += 1
            
            # Show progress every 20 requests
            if request_count % 20 == 0:
                elapsed = (time.time() - start_time) / 60
                print(f"📊 {elapsed:.1f}min: {request_count} requests ({success_count} successful)")
            
            # Variable delay to simulate realistic usage
            await asyncio.sleep(random.uniform(1.0, 5.0))
    
    print(f"\n🎉 Completed! {success_count}/{request_count} requests successful")
    return success_count

async def main():
    """Main function."""
    print("🌐 API Traffic Generator")
    print("=" * 40)
    print(f"🔑 Using API key: {API_KEY[:20]}...")
    
    print("\nChoose traffic generation mode:")
    print("1. Quick burst (50 requests)")
    print("2. Medium burst (200 requests)")
    print("3. Continuous traffic (10 minutes)")
    print("4. Long continuous traffic (60 minutes)")
    
    try:
        choice = input("Select option (1-4): ").strip()
        
        if choice == "1":
            await generate_burst_traffic(50)
        elif choice == "2":
            await generate_burst_traffic(200)
        elif choice == "3":
            await generate_continuous_traffic(10)
        elif choice == "4":
            await generate_continuous_traffic(60)
        else:
            print("Invalid choice. Running quick burst...")
            await generate_burst_traffic(50)
            
    except KeyboardInterrupt:
        print("\n⏹️  Traffic generation stopped by user.")
    except EOFError:
        print("Running default quick burst...")
        await generate_burst_traffic(50)
    
    print("\n📈 Check your analytics dashboard to see the generated data!")

if __name__ == "__main__":
    asyncio.run(main())