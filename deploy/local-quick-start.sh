#!/bin/bash
# Quick start script for local development - one command to run everything

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== API Developer Portal - Local Quick Start ===${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Change to project root
cd "$(dirname "$0")/.."

# Create env files if they don't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOF
POSTGRES_DB=devportal
POSTGRES_USER=devportal_user
POSTGRES_PASSWORD=local_dev_password_123
DATABASE_URL=postgresql+asyncpg://devportal_user:local_dev_password_123@postgres:5432/devportal
REDIS_URL=redis://redis:6379/0
SECRET_KEY=local-secret-key-$(date +%s)
JWT_SECRET_KEY=local-jwt-key-$(date +%s)
EOF
fi

if [ ! -f .env.dev ]; then
    cp .env .env.dev
fi

echo -e "${YELLOW}Starting all services...${NC}"

# Use production compose if available (no profiles)
if [ -f "docker-compose.prod.yml" ]; then
    echo "Using docker-compose.prod.yml"
    docker-compose -f docker-compose.prod.yml up -d
else
    echo "Using docker-compose.yml with frontend profile"
    docker-compose --profile frontend up -d
fi

# Wait a bit
sleep 5

# Show status
echo -e "${GREEN}
=== Services Status ===
${NC}"
docker-compose ps

echo -e "${GREEN}
=== Application URLs ===

Frontend: http://localhost:3000
Backend: http://localhost:8000
API Docs: http://localhost:8000/docs

Note: Frontend build may take 3-5 minutes on first run.

To view logs:
  docker-compose logs -f

To stop all services:
  docker-compose down

For interactive management:
  ./deploy/run-local.sh
${NC}"