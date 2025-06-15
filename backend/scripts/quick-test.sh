#!/bin/bash
# Quick Test Runner - Simple validation of core functionality

set -e

echo "🧪 Quick Docker Test Validation"
echo "================================"

# Build test image
echo "🏗️  Building test image..."
docker build --target test -t api-portal-test . -q

# Run core tests inside container (bypassing entrypoint)
echo "🔍 Running core tests in Docker container..."
docker run --rm \
  -w /app \
  --entrypoint="" \
  api-portal-test \
  python scripts/test-core-only.py

echo ""
echo "✅ Quick validation completed!"
echo "💡 For comprehensive testing, use: ./scripts/run-docker-tests.sh"