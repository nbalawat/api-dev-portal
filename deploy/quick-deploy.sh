#!/bin/bash
# Quick deployment script for GCP VM
# This script sets up Docker, clones the repo, and starts the application

set -e  # Exit on error

echo "=== Starting Quick Deploy for API Developer Portal ==="

# Update system
echo "Updating system packages..."
sudo apt-get update -qq

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository (you'll need to replace this with your actual repo URL)
echo "Cloning repository..."
if [ -z "$REPO_URL" ]; then
    echo "ERROR: Please set REPO_URL environment variable"
    echo "Example: export REPO_URL=https://github.com/yourusername/api-developer-portal.git"
    exit 1
fi

# Clone to home directory
cd /home/$USER
if [ -d "api-developer-portal" ]; then
    echo "Repository already exists, pulling latest..."
    cd api-developer-portal
    git pull
else
    git clone $REPO_URL api-developer-portal
    cd api-developer-portal
fi

# Create environment file with demo values
echo "Creating environment configuration..."
cat > .env << 'EOF'
# Database
POSTGRES_DB=devportal
POSTGRES_USER=devportal_user
POSTGRES_PASSWORD=quickdemo123!
DATABASE_URL=postgresql+asyncpg://devportal_user:quickdemo123!@postgres:5432/devportal

# Redis
REDIS_URL=redis://redis:6379/0

# Security (CHANGE THESE IN PRODUCTION!)
SECRET_KEY=quick-demo-secret-key-change-me-123!
JWT_SECRET_KEY=quick-demo-jwt-secret-change-me-456!

# Backend
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
EOF

# Start Docker Compose
echo "Starting application with Docker Compose..."
# Run docker-compose with the new group permissions
sudo -u $USER docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Check service status
echo "Checking service status..."
sudo -u $USER docker-compose ps

# Get the external IP
EXTERNAL_IP=$(curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google")

echo "
=== Deployment Complete! ===

Your API Developer Portal is now running!

Frontend URL: http://$EXTERNAL_IP:3000
Backend API: http://$EXTERNAL_IP:8000
API Docs: http://$EXTERNAL_IP:8000/docs

Note: It may take a minute for all services to be fully ready.

To check logs:
  cd /home/$USER/api-developer-portal
  docker-compose logs -f

To stop services:
  docker-compose down

To restart services:
  docker-compose up -d
"