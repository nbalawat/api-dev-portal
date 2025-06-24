#!/bin/bash

echo "🔧 Fixing Next.js build error..."

# Stop all containers
echo "📦 Stopping containers..."
docker-compose down

# Remove old build artifacts
echo "🧹 Cleaning build artifacts..."
docker-compose run --rm frontend rm -rf .next node_modules package-lock.json

# Rebuild without cache
echo "🔨 Rebuilding frontend..."
docker-compose build --no-cache frontend

# Start all services
echo "🚀 Starting services..."
docker-compose --profile frontend up -d

echo "✅ Fix complete! Check logs with: docker-compose logs -f frontend"
echo "🌐 Access the app at http://localhost:3000"