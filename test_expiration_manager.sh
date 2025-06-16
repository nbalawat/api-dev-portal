#!/bin/bash

# Script to test expiration manager system in Docker environment

echo "Testing Expiration Manager System in Docker..."
echo "=============================================="

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Run the expiration manager tests in the backend container
docker-compose exec backend python tests/test_expiration_manager_docker.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Expiration manager tests completed successfully!"
    echo "The expiration management feature is working correctly."
else
    echo ""
    echo "❌ Expiration manager tests failed!"
    echo "Please check the output above for details."
    exit 1
fi