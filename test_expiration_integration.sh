#!/bin/bash

# Script to test complete expiration integration in Docker environment

echo "Testing Complete Expiration Integration in Docker..."
echo "===================================================="

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Copy integration test to container
docker cp backend/tests/test_expiration_integration_docker.py $(docker-compose ps -q backend):/app/tests/

# Run the expiration integration tests in the backend container
docker-compose exec backend python tests/test_expiration_integration_docker.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Expiration integration tests completed successfully!"
    echo "The complete expiration management system is working correctly."
else
    echo ""
    echo "❌ Expiration integration tests failed!"
    echo "Please check the output above for details."
    exit 1
fi