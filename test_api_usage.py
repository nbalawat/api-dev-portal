#!/usr/bin/env python3
"""
API Key Usage Testing Script

This script tests API key functionality by making authenticated requests
to the API endpoints and simulating real usage patterns.
"""

import requests
import time
import random
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_KEYS = []  # Will be populated with API keys from the dashboard

def test_api_key_auth(api_key, endpoint="/api/v1/profile"):
    """Test API key authentication on a protected endpoint"""
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def simulate_api_usage(api_key, num_requests=10, delay_range=(1, 5)):
    """Simulate realistic API usage patterns"""
    results = []
    
    for i in range(num_requests):
        print(f"Making request {i+1}/{num_requests} with API key: {api_key[:12]}...")
        
        result = test_api_key_auth(api_key)
        results.append({
            "timestamp": datetime.now().isoformat(),
            "request_number": i + 1,
            **result
        })
        
        if result["success"]:
            print(f"✅ Request {i+1} successful")
        else:
            print(f"❌ Request {i+1} failed: {result.get('status_code', 'Unknown error')}")
        
        # Random delay between requests to simulate real usage
        if i < num_requests - 1:
            delay = random.uniform(*delay_range)
            time.sleep(delay)
    
    return results

def test_rate_limiting(api_key, requests_per_minute=30):
    """Test rate limiting by making rapid requests"""
    print(f"\n🚀 Testing rate limiting with {requests_per_minute} requests per minute...")
    
    results = []
    interval = 60 / requests_per_minute  # seconds between requests
    
    for i in range(requests_per_minute):
        result = test_api_key_auth(api_key)
        results.append({
            "timestamp": datetime.now().isoformat(),
            "request_number": i + 1,
            **result
        })
        
        if result["success"]:
            print(f"✅ Request {i+1}: Success")
        elif result.get("status_code") == 429:
            print(f"🛑 Request {i+1}: Rate limited!")
            break
        else:
            print(f"❌ Request {i+1}: {result.get('status_code', 'Error')}")
        
        time.sleep(interval)
    
    return results

def test_permissions(api_key):
    """Test different API endpoints with different permission requirements"""
    endpoints = [
        ("/api/v1/profile", "read"),
        ("/api/v1/profile", "read"),  # Test same endpoint multiple times
        # Add more endpoints as they become available
    ]
    
    results = {}
    for endpoint, required_permission in endpoints:
        print(f"\n🔑 Testing {endpoint} (requires: {required_permission})")
        result = test_api_key_auth(api_key, endpoint)
        results[endpoint] = result
        
        if result["success"]:
            print(f"✅ Access granted to {endpoint}")
        else:
            print(f"❌ Access denied to {endpoint}: {result.get('status_code', 'Unknown')}")
    
    return results

def main():
    print("🧪 API Key Usage Testing Script")
    print("=" * 50)
    
    # You'll need to copy API keys from the dashboard and paste them here
    api_keys = [
        # "sk_prod_1234567890abcdef",  # Example - replace with real keys
        # "sk_dev_abcdef1234567890",   # Example - replace with real keys
    ]
    
    if not api_keys:
        print("⚠️  No API keys provided!")
        print("\n📋 Instructions:")
        print("1. Go to your dashboard at http://localhost:3001/dashboard")
        print("2. Create some API keys with different permissions")
        print("3. Copy the API keys and add them to the 'api_keys' list in this script")
        print("4. Run this script again")
        return
    
    for i, api_key in enumerate(api_keys):
        print(f"\n{'='*20} Testing API Key {i+1} {'='*20}")
        print(f"API Key: {api_key[:12]}...")
        
        # Test basic authentication
        print("\n1️⃣ Testing basic authentication...")
        auth_result = test_api_key_auth(api_key)
        print(f"Authentication: {'✅ Success' if auth_result['success'] else '❌ Failed'}")
        
        if auth_result["success"]:
            # Test realistic usage patterns
            print("\n2️⃣ Simulating realistic API usage...")
            usage_results = simulate_api_usage(api_key, num_requests=5)
            successful_requests = sum(1 for r in usage_results if r["success"])
            print(f"Successful requests: {successful_requests}/{len(usage_results)}")
            
            # Test permissions
            print("\n3️⃣ Testing permissions...")
            permission_results = test_permissions(api_key)
            
            # Test rate limiting (uncomment to test)
            # print("\n4️⃣ Testing rate limiting...")
            # rate_limit_results = test_rate_limiting(api_key, requests_per_minute=20)
        
        print(f"\n✅ Completed testing for API key {i+1}")
    
    print("\n🎉 All API key tests completed!")
    print("\n📊 Check your dashboard to see updated usage statistics:")
    print("   - Total API Calls should increase")
    print("   - Last Used timestamps should update")
    print("   - Recent Activity should show API usage")

if __name__ == "__main__":
    main()