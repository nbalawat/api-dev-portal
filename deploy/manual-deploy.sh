#!/bin/bash
# Manual deployment script - copies local code to VM

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if instance name is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide instance name${NC}"
    echo "Usage: ./manual-deploy.sh INSTANCE_NAME"
    echo "Example: ./manual-deploy.sh api-portal-demo-1750729992"
    exit 1
fi

INSTANCE_NAME="$1"
ZONE="us-central1-a"

echo -e "${GREEN}=== Manual Deployment to $INSTANCE_NAME ===${NC}"

# Create a deployment package
echo -e "${YELLOW}Creating deployment package...${NC}"
cd ..
tar -czf deploy.tar.gz \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='deploy.tar.gz' \
  .

echo -e "${YELLOW}Copying code to VM...${NC}"
gcloud compute scp deploy.tar.gz ubuntu@$INSTANCE_NAME:/home/ubuntu/ --zone=$ZONE

echo -e "${YELLOW}Deploying on VM...${NC}"
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='
cd /home/ubuntu
tar -xzf deploy.tar.gz -C /home/ubuntu/api-developer-portal --strip-components=1 || {
  mkdir -p api-developer-portal
  tar -xzf deploy.tar.gz -C api-developer-portal
}
cd api-developer-portal

# Create .env if it doesn't exist
if [ ! -f .env ]; then
  cat > .env << EOF
POSTGRES_DB=devportal
POSTGRES_USER=devportal_user
POSTGRES_PASSWORD=demo$(date +%s)
DATABASE_URL=postgresql+asyncpg://devportal_user:demo$(date +%s)@postgres:5432/devportal
REDIS_URL=redis://redis:6379/0
SECRET_KEY=demo-secret-$(date +%s)
JWT_SECRET_KEY=demo-jwt-$(date +%s)
EOF
fi

# Copy .env to .env.dev if it doesn't exist
if [ ! -f .env.dev ]; then
  cp .env .env.dev || true
fi

# Start backend services first (without frontend profile)
docker-compose up -d postgres redis backend

# Wait for backend to be healthy
echo "Waiting for backend services to be healthy..."
sleep 30

# Start frontend with profile (build in background)
echo "Starting frontend build (this may take a few minutes)..."
nohup docker-compose --profile frontend up -d frontend > /tmp/frontend-build.log 2>&1 &

# Check backend services
docker-compose ps

echo ""
echo "Backend services started. Frontend build is running in background."
echo "Frontend build logs: /tmp/frontend-build.log"
echo "To check frontend status: docker ps | grep frontend"
'

# Cleanup
rm -f deploy.tar.gz

echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo "Check your app at:"
echo "- Frontend: http://$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'):3000"
echo "- Backend: http://$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'):8000"