#!/bin/bash

# Script to test enhanced rate limiting system in Docker environment

echo "Testing Enhanced Rate Limiting System in Docker..."
echo "=================================================="

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Copy test file to container
docker cp backend/tests/test_enhanced_rate_limiting_docker.py $(docker-compose ps -q backend):/app/tests/

# Run the enhanced rate limiting tests in the backend container
docker-compose exec backend python tests/test_enhanced_rate_limiting_docker.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Enhanced rate limiting tests completed successfully!"
    echo "The enhanced rate limiting system is working correctly."
else
    echo ""
    echo "❌ Enhanced rate limiting tests failed!"
    echo "Please check the output above for details."
    exit 1
fi