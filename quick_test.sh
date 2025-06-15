#!/bin/bash
# Quick API Key Testing Script
# Usage: ./quick_test.sh YOUR_API_KEY

if [ -z "$1" ]; then
    echo "Usage: ./quick_test.sh YOUR_API_KEY"
    exit 1
fi

API_KEY=$1
BASE_URL="http://localhost:8000"

echo "🧪 Testing API Key: ${API_KEY:0:12}..."
echo "========================================"

# Test 1: Single request
echo "📡 Test 1: Single authentication test"
curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" "$BASE_URL/api/v1/profile" | jq . || echo "Response received"
echo -e "\n"

# Test 2: Multiple requests to generate usage
echo "📊 Test 2: Making 5 requests to generate usage statistics..."
for i in {1..5}; do
    echo "Request $i/5..."
    response=$(curl -s -w "HTTP_STATUS:%{http_code}" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" "$BASE_URL/api/v1/profile")
    http_status=$(echo $response | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
    
    if [ "$http_status" = "200" ]; then
        echo "✅ Success (Status: $http_status)"
    else
        echo "❌ Failed (Status: $http_status)"
    fi
    
    # Small delay between requests
    sleep 1
done

echo -e "\n🎉 Test completed!"
echo "📈 Check your dashboard now - you should see:"
echo "   - Total API Calls increased by 6"
echo "   - Last Used updated to 'just now'"
echo "   - Recent Activity shows 'API Key Used'"
echo "   - Active API Keys count"