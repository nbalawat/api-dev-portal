#!/bin/bash
set -e

# CI/CD Test Execution Script
# Sequential execution for maximum reliability

echo "🚀 API Developer Portal - CI/CD Test Suite"
echo "============================================"
echo ""

# Function to run tests with retry mechanism
run_tests_with_retry() {
    local test_type="$1"
    local max_retries=2
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        echo "🧪 Running $test_type tests (attempt $((retry_count + 1))/$max_retries)..."
        
        if docker-compose -f docker-compose.test.yml run --rm integration-tests \
            python -m pytest tests/test_integration_auth.py -v \
            --maxfail=1 \
            -x \
            --tb=short; then
            echo "✅ $test_type tests passed!"
            return 0
        else
            echo "❌ $test_type tests failed on attempt $((retry_count + 1))"
            retry_count=$((retry_count + 1))
            
            if [ $retry_count -lt $max_retries ]; then
                echo "🔄 Retrying in 5 seconds..."
                sleep 5
            fi
        fi
    done
    
    echo "💥 $test_type tests failed after $max_retries attempts"
    return 1
}

# Main execution
echo "🔧 Setting up test environment..."
docker-compose -f docker-compose.test.yml up -d test-postgres test-redis

# Wait for services to be ready with health checks
echo "⏳ Waiting for database and Redis to be ready..."
echo "🔍 Checking PostgreSQL health..."
for i in {1..30}; do
    if docker-compose -f docker-compose.test.yml exec -T test-postgres pg_isready -U testuser -d testdb > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    echo "⏳ PostgreSQL not ready yet (attempt $i/30)..."
    sleep 2
done

echo "🔍 Checking Redis health..."
for i in {1..30}; do
    if docker-compose -f docker-compose.test.yml exec -T test-redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is ready"
        break
    fi
    echo "⏳ Redis not ready yet (attempt $i/30)..."
    sleep 2
done

echo "🔧 Additional initialization delay..."
sleep 5

# Run integration tests with retry
if run_tests_with_retry "Integration"; then
    echo ""
    echo "🎉 All tests passed successfully!"
    echo "✅ CI/CD test suite completed"
    exit 0
else
    echo ""
    echo "💥 Test suite failed"
    echo "❌ CI/CD test suite failed"
    exit 1
fi