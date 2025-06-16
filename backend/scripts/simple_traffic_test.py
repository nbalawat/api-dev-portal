#!/usr/bin/env python3
"""
Simple script to test API endpoints and generate some traffic.
You can modify the API_KEY variable below with a valid key from your dashboard.
"""
import asyncio
import aiohttp
import time

# API Configuration
API_BASE_URL = "http://localhost:8000"

# REPLACE THIS WITH A VALID API KEY FROM YOUR DASHBOARD
API_KEY = "sk_PbPz0_WgKpNP0U3-1sjJCRpFcKKNuLpVgwcqQ_GwYnc"

# Test endpoints
ENDPOINTS = [
    {"method": "GET", "path": "/api/v1/profile"},
    {"method": "GET", "path": "/api/v1/api-key/info"},
    {"method": "GET", "path": "/api/analytics/summary"},
    {"method": "GET", "path": "/api/analytics/endpoints"},
    {"method": "POST", "path": "/api/analytics/time-series", "body": {"metric": "requests", "timeframe": "day", "interval": "hour"}},
]

async def test_endpoint(session, endpoint):
    """Test a single endpoint."""
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
            async with session.post(url, headers=headers, json=endpoint.get("body", {})) as response:
                response_time = (time.time() - start_time) * 1000
                status = response.status
                text = await response.text()
        
        print(f"✅ {endpoint['method']} {endpoint['path']} -> {status} ({response_time:.1f}ms)")
        if status >= 400:
            print(f"   Error: {text[:200]}")
        return True
        
    except Exception as e:
        print(f"❌ {endpoint['method']} {endpoint['path']} -> Error: {e}")
        return False

async def main():
    """Test all endpoints."""
    print("🧪 Simple API Traffic Test")
    print("=" * 40)
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Please set a valid API_KEY in the script!")
        print("   1. Go to your dashboard (http://localhost:3000)")
        print("   2. Create or copy an API key")
        print("   3. Replace 'YOUR_API_KEY_HERE' in this script")
        return
    
    print(f"🔑 Using API key: {API_KEY[:12]}...")
    
    async with aiohttp.ClientSession() as session:
        success_count = 0
        
        for endpoint in ENDPOINTS:
            success = await test_endpoint(session, endpoint)
            if success:
                success_count += 1
            
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        print(f"\n📊 Results: {success_count}/{len(ENDPOINTS)} endpoints successful")
        
        if success_count > 0:
            print("🎉 Great! Your API key is working and generating traffic data.")
            print("📈 Check your analytics dashboard to see the data.")
        else:
            print("❌ No endpoints were successful. Check your API key and permissions.")

if __name__ == "__main__":
    asyncio.run(main())