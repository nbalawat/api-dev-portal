#!/bin/bash
# Optimized deployment script for GCP
# Uses docker-compose.prod.yml without profiles for faster deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== API Developer Portal - Optimized GCP Deploy ===${NC}"

# Default service account path (hardcoded)
DEFAULT_SA_PATH="/Users/nbalawat/development/scalable-rag-pipeline-with-access-entitlements/infrastructure/service-accounts/deploy-dev-sa.json"

# Check if using Application Default Credentials
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${GREEN}Using Application Default Credentials${NC}"
    echo "  File: $GOOGLE_APPLICATION_CREDENTIALS"
    
    # Verify file exists
    if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo -e "${RED}Error: Service account file not found${NC}"
        exit 1
    fi
elif [ -f "$DEFAULT_SA_PATH" ]; then
    # Use default hardcoded path
    echo -e "${GREEN}Using default service account${NC}"
    echo "  File: $DEFAULT_SA_PATH"
    export GOOGLE_APPLICATION_CREDENTIALS="$DEFAULT_SA_PATH"
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    # Try environment variable
    if [ -n "$GCP_PROJECT_ID" ]; then
        PROJECT_ID="$GCP_PROJECT_ID"
    elif [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        # Try to extract from service account JSON
        PROJECT_ID=$(grep -o '"project_id"[[:space:]]*:[[:space:]]*"[^"]*"' "$GOOGLE_APPLICATION_CREDENTIALS" | sed 's/.*"\([^"]*\)"$/\1/')
        echo -e "${GREEN}Extracted project ID from service account: $PROJECT_ID${NC}"
    elif [ -f "$DEFAULT_SA_PATH" ]; then
        # Try to extract from default service account JSON
        PROJECT_ID=$(grep -o '"project_id"[[:space:]]*:[[:space:]]*"[^"]*"' "$DEFAULT_SA_PATH" | sed 's/.*"\([^"]*\)"$/\1/')
        echo -e "${GREEN}Extracted project ID from service account: $PROJECT_ID${NC}"
    fi
    
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Error: No GCP project found${NC}"
        echo "Option 1: Set environment variable"
        echo "  export GCP_PROJECT_ID=your-project-id"
        echo "Option 2: Use gcloud config"
        echo "  gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
    
    # Set the project
    gcloud config set project "$PROJECT_ID" --quiet
fi

echo -e "${YELLOW}Using project: $PROJECT_ID${NC}"

# Set variables
INSTANCE_NAME="api-portal-demo-$(date +%s)"
ZONE="us-central1-a"
MACHINE_TYPE="e2-medium"

# Get the repository URL
echo -e "${YELLOW}Enter your repository URL (or press Enter to use this repo):${NC}"
read -p "Repository URL: " REPO_URL
if [ -z "$REPO_URL" ]; then
    # Try to get the current repo URL
    REPO_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
    if [ -z "$REPO_URL" ]; then
        echo -e "${RED}Error: Could not determine repository URL${NC}"
        echo "Please provide the repository URL"
        exit 1
    fi
fi

echo -e "${GREEN}Using repository: $REPO_URL${NC}"

# Create the startup script
STARTUP_SCRIPT=$(cat << 'SCRIPT_END'
#!/bin/bash
export REPO_URL="REPO_URL_PLACEHOLDER"

# Log output
exec > >(tee -a /var/log/startup-script.log)
exec 2>&1

echo "Starting deployment at $(date)"

# Update system
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repository
cd /home/ubuntu
sudo -u ubuntu git clone $REPO_URL api-developer-portal
cd api-developer-portal

# Create environment file
cat > .env << 'EOF'
POSTGRES_DB=devportal
POSTGRES_USER=devportal_user
POSTGRES_PASSWORD=demo$(date +%s)
DATABASE_URL=postgresql+asyncpg://devportal_user:demo$(date +%s)@postgres:5432/devportal
REDIS_URL=redis://redis:6379/0
SECRET_KEY=demo-secret-$(date +%s)
JWT_SECRET_KEY=demo-jwt-$(date +%s)
EOF

# Copy .env to .env.dev
cp .env .env.dev
chown ubuntu:ubuntu .env .env.dev

# Use production compose file if available
if [ -f "docker-compose.prod.yml" ]; then
    echo "Using docker-compose.prod.yml"
    COMPOSE_FILE="docker-compose.prod.yml"
else
    echo "Using docker-compose.yml"
    COMPOSE_FILE="docker-compose.yml"
fi

# Start backend services first
echo "Starting backend services..."
sudo -u ubuntu /usr/local/bin/docker-compose -f $COMPOSE_FILE up -d postgres redis backend

# Wait for backend to be healthy
echo "Waiting for backend services to be healthy..."
sleep 30

# Start frontend (this will build in the foreground for better reliability)
echo "Building and starting frontend..."
sudo -u ubuntu /usr/local/bin/docker-compose -f $COMPOSE_FILE up -d frontend

# Final check
echo "Checking all services..."
sudo -u ubuntu /usr/local/bin/docker-compose -f $COMPOSE_FILE ps

echo ""
echo "Deployment completed at $(date)"
echo "All services should be running. Frontend may take a few more minutes to build."
SCRIPT_END
)

# Replace the repository URL in the startup script
STARTUP_SCRIPT="${STARTUP_SCRIPT//REPO_URL_PLACEHOLDER/$REPO_URL}"

# Create temporary file for startup script
TEMP_FILE=$(mktemp)
echo "$STARTUP_SCRIPT" > "$TEMP_FILE"

echo -e "${YELLOW}Creating VM instance...${NC}"

# Create the instance with larger machine type for faster builds
gcloud compute instances create "$INSTANCE_NAME" \
  --machine-type="$MACHINE_TYPE" \
  --boot-disk-size=30GB \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=api-portal \
  --metadata-from-file startup-script="$TEMP_FILE" \
  --zone="$ZONE"

# Clean up temp file
rm "$TEMP_FILE"

echo -e "${YELLOW}Creating firewall rules...${NC}"

# Create firewall rules if they don't exist
if ! gcloud compute firewall-rules describe allow-api-portal &>/dev/null; then
    gcloud compute firewall-rules create allow-api-portal \
      --allow tcp:3000,tcp:8000 \
      --source-ranges=0.0.0.0/0 \
      --target-tags=api-portal \
      --description="Allow access to API Portal"
else
    echo "Firewall rule 'allow-api-portal' already exists"
fi

# Get external IP
echo -e "${YELLOW}Waiting for external IP...${NC}"
sleep 5

EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
  --zone="$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo -e "${GREEN}
=== Deployment Complete! ===

Instance Name: $INSTANCE_NAME
External IP: $EXTERNAL_IP

Your application will be available at:
- Frontend: http://$EXTERNAL_IP:3000
- Backend API: http://$EXTERNAL_IP:8000
- API Docs: http://$EXTERNAL_IP:8000/docs

Note: Frontend build may take 3-5 minutes to complete.

To check the deployment progress:
  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='tail -f /var/log/startup-script.log'

To SSH into the instance:
  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE

To check Docker services:
  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd ~/api-developer-portal && sudo docker-compose ps'

To monitor frontend build:
  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd ~/api-developer-portal && sudo docker-compose logs -f frontend'

To delete this instance when done:
  gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE

Or use our cleanup script:
  ./deploy/cleanup.sh
${NC}"

# Save instance details
echo "$INSTANCE_NAME,$ZONE,$EXTERNAL_IP" >> deploy/.deployed-instances

# Ask if user wants to monitor the deployment
echo -e "${YELLOW}Would you like to monitor the deployment progress? (y/n)${NC}"
read -p "Monitor? " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Monitoring deployment (press Ctrl+C to stop)...${NC}"
    sleep 10  # Give the instance time to start
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command='tail -f /var/log/startup-script.log'
fi