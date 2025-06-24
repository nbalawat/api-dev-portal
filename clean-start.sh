#!/bin/bash

echo "🧹 Complete Clean Start for API Developer Portal"
echo "================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Stop and remove everything
echo "📦 Removing all containers, networks, and volumes..."
docker-compose down -v --remove-orphans

# Remove any dangling images
echo "🗑️  Cleaning up Docker images..."
docker image prune -f

# Remove frontend build artifacts from host if they exist
echo "🧹 Cleaning frontend build artifacts..."
rm -rf frontend/.next frontend/node_modules frontend/package-lock.json

# Create fresh .env files if they don't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
fi

# Build everything fresh
echo "🔨 Building all services from scratch..."
docker-compose build --no-cache

# Start all services
echo "🚀 Starting all services..."
docker-compose --profile frontend up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Show status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Clean start complete!"
echo ""
echo "🌐 Access points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "🔑 Default credentials:"
echo "   - Email: admin@example.com"
echo "   - Password: admin123"
echo ""
echo "📋 Useful commands:"
echo "   - View logs: docker-compose logs -f frontend"
echo "   - Stop all: docker-compose down"
echo "   - Restart frontend: docker-compose restart frontend"