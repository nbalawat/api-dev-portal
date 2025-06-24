#!/bin/bash
# Script to fix frontend on existing deployments

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if instance name is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide instance name${NC}"
    echo "Usage: ./fix-frontend.sh INSTANCE_NAME"
    echo "Example: ./fix-frontend.sh api-portal-demo-1750729992"
    exit 1
fi

INSTANCE_NAME="$1"
ZONE="${2:-us-central1-a}"

echo -e "${GREEN}=== Fixing Frontend on $INSTANCE_NAME ===${NC}"

# SSH and fix frontend
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='
cd /home/ubuntu/api-developer-portal

# Copy .env to .env.dev if missing
if [ ! -f .env.dev ]; then
  sudo cp .env .env.dev
  sudo chown ubuntu:ubuntu .env.dev
fi

# Check if frontend is already running
if sudo docker ps | grep -q frontend; then
  echo "Frontend is already running!"
  exit 0
fi

echo "Starting frontend container..."

# Try with production compose file first
if [ -f "docker-compose.prod.yml" ]; then
  echo "Using docker-compose.prod.yml"
  sudo docker-compose -f docker-compose.prod.yml up -d frontend
else
  # Use regular compose with profile
  echo "Using docker-compose.yml with profile"
  sudo docker-compose --profile frontend up -d frontend
fi

echo ""
echo "Frontend build started. This may take 3-5 minutes."
echo "You can monitor the build with:"
echo "  sudo docker-compose logs -f frontend"
'

echo -e "${GREEN}Frontend fix initiated!${NC}"
echo ""
echo "To monitor frontend build progress:"
echo -e "${YELLOW}gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd ~/api-developer-portal && sudo docker-compose logs -f frontend'${NC}"