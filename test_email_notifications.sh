#!/bin/bash

# Script to test email notifications in Docker environment

echo "Testing Email Notification System in Docker..."
echo "=============================================="

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Run the email notification tests in the backend container
docker-compose exec backend python tests/test_email_notifications_docker.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Email notification tests completed successfully!"
    echo "The email notification feature is working correctly."
else
    echo ""
    echo "❌ Email notification tests failed!"
    echo "Please check the output above for details."
    exit 1
fi