#!/bin/bash

# Script to test complete system integration in Docker environment

echo "Testing Complete System Integration in Docker..."
echo "==============================================="

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Copy test file to container
docker cp backend/tests/test_complete_system_integration_docker.py $(docker-compose ps -q backend):/app/tests/

# Run the complete system integration tests in the backend container
docker-compose exec backend python tests/test_complete_system_integration_docker.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Complete system integration tests completed successfully!"
    echo "All features are working correctly and properly integrated!"
    echo ""
    echo "🚀 READY FOR PRODUCTION:"
    echo "   ✅ API key expiration management"
    echo "   ✅ Enhanced rate limiting with burst protection"
    echo "   ✅ Background task automation"
    echo "   ✅ Email notification system"
    echo "   ✅ Comprehensive monitoring and analytics"
    echo ""
else
    echo ""
    echo "❌ Complete system integration tests failed!"
    echo "Please check the output above for details."
    exit 1
fi