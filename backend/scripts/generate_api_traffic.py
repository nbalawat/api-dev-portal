#!/usr/bin/env python3
"""
Script to generate realistic API traffic by hitting protected endpoints.
This will create real usage data that gets tracked by the middleware.
"""
import asyncio
import aiohttp
import random
import time
from datetime import datetime, timedelta
import json
from typing import List, Dict

# API base URL
API_BASE_URL = "http://localhost:8000"

# Protected endpoints to hit
PROTECTED_ENDPOINTS = [
    {
        "method": "GET",
        "path": "/api/v1/profile",
        "weight": 0.3,
        "scopes_required": ["read"]
    },
    {
        "method": "GET", 
        "path": "/api/v1/api-key/info",
        "weight": 0.2,
        "scopes_required": ["read"]
    },
    {
        "method": "GET",
        "path": "/api/v1/api-key/usage-stats", 
        "weight": 0.15,
        "scopes_required": ["analytics"]
    },
    {
        "method": "GET",
        "path": "/api/analytics/summary",
        "weight": 0.1,
        "scopes_required": ["analytics"]
    },
    {
        "method": "GET",
        "path": "/api/analytics/endpoints",
        "weight": 0.1,
        "scopes_required": ["analytics"]
    },
    {
        "method": "GET",
        "path": "/api/api-keys/",
        "weight": 0.05,
        "scopes_required": ["read"]
    },
    {
        "method": "POST",
        "path": "/api/v1/test-endpoint",
        "weight": 0.05,
        "scopes_required": ["write"],
        "body": {"test": "data", "timestamp": ""}
    },
    {
        "method": "POST",
        "path": "/api/analytics/time-series",
        "weight": 0.05,
        "scopes_required": ["analytics"],
        "body": {
            "metric": "requests",
            "timeframe": "day",
            "interval": "hour"
        }
    }
]

def weighted_choice(choices: List[Dict]) -> Dict:
    """Choose a random endpoint based on weights."""
    total = sum(endpoint["weight"] for endpoint in choices)
    r = random.uniform(0, total)
    upto = 0
    for endpoint in choices:
        if upto + endpoint["weight"] >= r:
            return endpoint
        upto += endpoint["weight"]
    return choices[-1]  # fallback

async def make_request(session: aiohttp.ClientSession, endpoint: Dict, api_key: str) -> Dict:
    """Make a request to an endpoint with the given API key."""
    url = f"{API_BASE_URL}{endpoint['path']}"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        # Prepare request data
        kwargs = {
            "headers": headers,
            "timeout": aiohttp.ClientTimeout(total=10)
        }
        
        if endpoint["method"] == "POST" and "body" in endpoint:
            body = endpoint["body"].copy()
            if "timestamp" in body:
                body["timestamp"] = datetime.utcnow().isoformat()
            kwargs["json"] = body
        
        # Add query parameters for GET requests
        if endpoint["method"] == "GET" and "analytics" in endpoint["path"]:
            kwargs["params"] = {"timeframe": random.choice(["hour", "day", "week"])}
        
        # Make the request
        async with session.request(endpoint["method"], url, **kwargs) as response:
            response_text = await response.text()
            
            return {
                "endpoint": endpoint["path"],
                "method": endpoint["method"],
                "status_code": response.status,
                "response_time_ms": 0,  # Will be calculated by caller
                "success": 200 <= response.status < 400,
                "response_size": len(response_text),
                "error": None if 200 <= response.status < 400 else response_text[:200]
            }
    
    except asyncio.TimeoutError:
        return {
            "endpoint": endpoint["path"],
            "method": endpoint["method"],
            "status_code": 408,
            "response_time_ms": 10000,
            "success": False,
            "response_size": 0,
            "error": "Request timeout"
        }
    except Exception as e:
        return {
            "endpoint": endpoint["path"],
            "method": endpoint["method"],
            "status_code": 500,
            "response_time_ms": 0,
            "success": False,
            "response_size": 0,
            "error": str(e)[:200]
        }

async def get_api_keys() -> List[str]:
    """Get list of API keys from the backend."""
    url = f"{API_BASE_URL}/health"
    
    print("🔍 Checking if backend is accessible...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    print("✅ Backend is accessible")
                else:
                    print(f"❌ Backend returned status {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return []
    
    # For now, we'll need user to provide API keys
    # In a real scenario, you might query the database or have a config file
    print("\n📋 To generate traffic, you need valid API keys.")
    print("You can find API keys in your dashboard or create new ones.")
    print("Enter API keys one by one (press Enter with empty line to finish):")
    
    api_keys = []
    while True:
        key = input(f"API Key {len(api_keys) + 1} (or press Enter to finish): ").strip()
        if not key:
            break
        api_keys.append(key)
    
    return api_keys

async def generate_traffic_burst(api_keys: List[str], duration_minutes: int = 5) -> Dict:
    """Generate a burst of traffic over the specified duration."""
    print(f"🚀 Generating traffic for {duration_minutes} minutes...")
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    results = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "endpoints_hit": set(),
        "response_times": [],
        "errors": []
    }
    
    async with aiohttp.ClientSession() as session:
        while time.time() < end_time:
            # Choose random API key and endpoint
            api_key = random.choice(api_keys)
            endpoint = weighted_choice(PROTECTED_ENDPOINTS)
            
            # Make the request
            request_start = time.time()
            result = await make_request(session, endpoint, api_key)
            request_time = (time.time() - request_start) * 1000  # Convert to ms
            
            # Update results
            results["total_requests"] += 1
            results["endpoints_hit"].add(f"{result['method']} {result['endpoint']}")
            results["response_times"].append(request_time)
            
            if result["success"]:
                results["successful_requests"] += 1
                print(f"✅ {result['method']} {result['endpoint']} -> {result['status_code']} ({request_time:.1f}ms)")
            else:
                results["failed_requests"] += 1
                results["errors"].append(result["error"])
                print(f"❌ {result['method']} {result['endpoint']} -> {result['status_code']} ({request_time:.1f}ms) - {result['error']}")
            
            # Random delay between requests (simulate realistic usage)
            await asyncio.sleep(random.uniform(0.1, 2.0))
    
    return results

async def generate_background_traffic(api_keys: List[str], duration_minutes: int = 60) -> Dict:
    """Generate steady background traffic over a longer period."""
    print(f"📈 Generating background traffic for {duration_minutes} minutes...")
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    results = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "endpoints_hit": set(),
        "response_times": [],
        "errors": []
    }
    
    async with aiohttp.ClientSession() as session:
        while time.time() < end_time:
            # Choose random API key and endpoint
            api_key = random.choice(api_keys)
            endpoint = weighted_choice(PROTECTED_ENDPOINTS)
            
            # Make the request
            request_start = time.time()
            result = await make_request(session, endpoint, api_key)
            request_time = (time.time() - request_start) * 1000
            
            # Update results
            results["total_requests"] += 1
            results["endpoints_hit"].add(f"{result['method']} {result['endpoint']}")
            results["response_times"].append(request_time)
            
            if result["success"]:
                results["successful_requests"] += 1
            else:
                results["failed_requests"] += 1
                results["errors"].append(result["error"])
            
            # Show progress every 10 requests
            if results["total_requests"] % 10 == 0:
                print(f"📊 Progress: {results['total_requests']} requests, "
                      f"{results['successful_requests']} successful, "
                      f"{results['failed_requests']} failed")
            
            # Longer delay for background traffic
            await asyncio.sleep(random.uniform(2.0, 10.0))
    
    return results

def print_results(results: Dict):
    """Print traffic generation results."""
    print("\n" + "="*50)
    print("📊 TRAFFIC GENERATION RESULTS")
    print("="*50)
    print(f"Total Requests: {results['total_requests']}")
    print(f"Successful: {results['successful_requests']}")
    print(f"Failed: {results['failed_requests']}")
    print(f"Success Rate: {(results['successful_requests']/results['total_requests']*100):.1f}%")
    
    if results['response_times']:
        avg_response_time = sum(results['response_times']) / len(results['response_times'])
        print(f"Average Response Time: {avg_response_time:.1f}ms")
    
    print(f"\nEndpoints Hit ({len(results['endpoints_hit'])}):")
    for endpoint in sorted(results['endpoints_hit']):
        print(f"  - {endpoint}")
    
    if results['errors']:
        print(f"\nSample Errors ({len(results['errors'])}):")
        for error in list(set(results['errors']))[:5]:
            print(f"  - {error}")

async def main():
    """Main function to generate API traffic."""
    print("🌐 API Traffic Generator")
    print("=" * 50)
    
    # Get API keys
    api_keys = await get_api_keys()
    if not api_keys:
        print("❌ No API keys provided. Exiting.")
        return
    
    print(f"🔑 Using {len(api_keys)} API key(s)")
    
    # Choose traffic type
    print("\nChoose traffic generation mode:")
    print("1. Quick burst (5 minutes of intense traffic)")
    print("2. Background traffic (60 minutes of steady traffic)")
    print("3. Custom duration")
    
    choice = input("Select option (1-3): ").strip()
    
    if choice == "1":
        results = await generate_traffic_burst(api_keys, 5)
    elif choice == "2":
        results = await generate_background_traffic(api_keys, 60)
    elif choice == "3":
        duration = int(input("Enter duration in minutes: "))
        mode = input("Burst (b) or background (g) traffic? ").strip().lower()
        if mode.startswith('b'):
            results = await generate_traffic_burst(api_keys, duration)
        else:
            results = await generate_background_traffic(api_keys, duration)
    else:
        print("Invalid choice. Using quick burst mode.")
        results = await generate_traffic_burst(api_keys, 5)
    
    print_results(results)
    print("\n✅ Traffic generation complete!")
    print("📈 Check your analytics dashboard to see the generated data.")

if __name__ == "__main__":
    asyncio.run(main())