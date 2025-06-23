# Quick GCP Deployment Guide

This guide will help you deploy the API Developer Portal to Google Cloud Platform in under 10 minutes.

## Prerequisites
- Google Cloud account with billing enabled
- `gcloud` CLI installed locally (or use Cloud Shell)

## Option 1: One-Click Deployment (Recommended - 5 minutes)

Run this single command from your local machine:

```bash
# From the project root directory
./deploy/one-click-deploy.sh
```

This script will:
1. Create a GCP VM instance
2. Install Docker and Docker Compose
3. Clone your repository
4. Start all services
5. Open firewall ports
6. Give you the URLs to access your app

## Option 2: Manual VM Deployment

### Step 1: Set your project and repo URL
```bash
# Set your GCP project
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# Set your repository URL
export REPO_URL=https://github.com/yourusername/api-developer-portal.git
```

### Step 2: Create the VM with auto-deployment
```bash
# Create VM with startup script
gcloud compute instances create api-portal-demo \
  --machine-type=e2-medium \
  --boot-disk-size=30GB \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=api-portal \
  --metadata=REPO_URL=$REPO_URL,startup-script='#!/bin/bash
curl -s https://raw.githubusercontent.com/yourusername/api-developer-portal/main/deploy/quick-deploy.sh | bash' \
  --zone=us-central1-a
```

### Step 3: Open firewall ports
```bash
# Allow access to frontend and backend
gcloud compute firewall-rules create allow-api-portal \
  --allow tcp:3000,tcp:8000 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=api-portal \
  --description="Allow access to API Portal frontend and backend"
```

### Step 4: Get your external IP
```bash
# Get the external IP
gcloud compute instances describe api-portal-demo \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

### Step 5: Access your application
- Frontend: `http://[EXTERNAL-IP]:3000`
- Backend API: `http://[EXTERNAL-IP]:8000`
- API Documentation: `http://[EXTERNAL-IP]:8000/docs`

## Option 3: Cloud Shell Deployment (No Local Setup)

### Step 1: Open Cloud Shell
Click the Cloud Shell icon in the GCP Console

### Step 2: Clone and deploy
```bash
# Clone your repository
git clone https://github.com/yourusername/api-developer-portal.git
cd api-developer-portal

# Create environment file
cat > .env << 'EOF'
POSTGRES_DB=devportal
POSTGRES_USER=devportal_user
POSTGRES_PASSWORD=demo123
DATABASE_URL=postgresql+asyncpg://devportal_user:demo123@postgres:5432/devportal
REDIS_URL=redis://redis:6379/0
SECRET_KEY=demo-secret-key-123
JWT_SECRET_KEY=demo-jwt-key-456
EOF

# Start services
docker-compose up -d
```

### Step 3: Access via Web Preview
1. Click the "Web Preview" button in Cloud Shell
2. Change the port to 3000
3. Open in a new window

## Checking Status

### View logs
```bash
# SSH into your VM
gcloud compute ssh api-portal-demo --zone=us-central1-a

# Check logs
cd ~/api-developer-portal
docker-compose logs -f
```

### Restart services
```bash
docker-compose restart
```

### Stop services
```bash
docker-compose down
```

## Clean Up

To avoid charges, use our cleanup scripts:

### Automatic Cleanup (Recommended)
```bash
# Interactive cleanup - choose what to delete
./deploy/cleanup.sh

# OR force delete everything (no prompts)
./deploy/cleanup-all.sh
```

### Manual Cleanup
```bash
# Delete specific VM
gcloud compute instances delete api-portal-demo --zone=us-central1-a

# Delete firewall rule
gcloud compute firewall-rules delete allow-api-portal
```

The cleanup scripts will:
- Find all instances tagged with 'api-portal'
- Delete associated firewall rules
- Show you what was cleaned up
- Estimate your savings (~$24-48/month per instance)

## Troubleshooting

### Services not accessible
1. Check firewall rules are created
2. Verify services are running: `docker-compose ps`
3. Check logs: `docker-compose logs`

### Out of memory
- Upgrade to a larger machine type (e2-medium or e2-standard-2)

### Can't connect to database
- Ensure all services are running
- Check environment variables in .env file

## Next Steps

For a production deployment:
1. Use Cloud SQL instead of containerized PostgreSQL
2. Use Memorystore instead of containerized Redis
3. Set up HTTPS with a load balancer
4. Use Cloud Run or GKE for better scaling
5. Set up proper secrets management
6. Configure backups and monitoring