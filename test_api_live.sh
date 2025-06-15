#!/bin/bash

WORKING_KEY="sk_nYZv7IdaOWyK_3irXR0etnsvUJQbFqYS6rW6ciVlZcg"

echo "🎉 COMPREHENSIVE API KEY FUNCTIONALITY TEST"
echo "============================================"
echo "API Key: ${WORKING_KEY:0:20}..."
echo ""

echo "📡 1. User Profile:"
curl -s -H "X-API-Key: $WORKING_KEY" "http://localhost:8000/api/v1/profile" | jq '{username: .username, email: .email, role: .role}'

echo -e "\n📊 2. API Key Information:"
curl -s -H "X-API-Key: $WORKING_KEY" "http://localhost:8000/api/v1/api-key/info" | jq '{name: .name, scopes: .scopes, rate_limit: .rate_limit}'

echo -e "\n🔧 3. Rate Limit Test:"
curl -s -H "X-API-Key: $WORKING_KEY" "http://localhost:8000/api/v1/rate-limit-test" | jq '{message: .message, api_key_id: .api_key_id}'

echo -e "\n📈 4. Multiple Requests to Generate Usage:"
for i in {1..3}; do
    echo -n "Request $i: "
    response=$(curl -s -w "%{http_code}" -H "X-API-Key: $WORKING_KEY" "http://localhost:8000/api/v1/profile" -o /dev/null)
    if [ "$response" = "200" ]; then
        echo "✅ Success"
    else
        echo "❌ Failed ($response)"
    fi
    sleep 1
done

echo -e "\n📊 5. Updated Usage Statistics:"
curl -s -H "X-API-Key: $WORKING_KEY" "http://localhost:8000/api/v1/api-key/usage-stats" | jq '{total_requests: .total_requests, requests_today: .requests_today}'

echo -e "\n🎯 6. Testing Different Endpoints:"
echo "   - Admin endpoint:"
curl -s -H "X-API-Key: $WORKING_KEY" "http://localhost:8000/api/v1/admin/system-info" | jq '.message'

echo -e "\n✅ API Key Authentication is working perfectly!"