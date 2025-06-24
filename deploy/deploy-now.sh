#!/bin/bash
# Super simple deployment with hardcoded service account
# Just run: ./deploy-now.sh YOUR_PROJECT_ID

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Hardcoded service account path
export GOOGLE_APPLICATION_CREDENTIALS="/Users/nbalawat/development/scalable-rag-pipeline-with-access-entitlements/infrastructure/service-accounts/deploy-dev-sa.json"

echo -e "${GREEN}=== Super Quick Deploy ===${NC}"

# Check if project ID is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide your GCP project ID${NC}"
    echo "Usage: ./deploy-now.sh YOUR_PROJECT_ID"
    exit 1
fi

export GCP_PROJECT_ID="$1"

# Check if service account exists
if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${RED}Error: Service account file not found at:${NC}"
    echo "$GOOGLE_APPLICATION_CREDENTIALS"
    exit 1
fi

echo -e "${GREEN}Using:${NC}"
echo "  Service Account: $GOOGLE_APPLICATION_CREDENTIALS"
echo "  Project ID: $GCP_PROJECT_ID"
echo ""

# Run quick setup (if needed)
echo -e "${YELLOW}Running setup...${NC}"
./deploy/quick-setup.sh

echo ""
echo -e "${YELLOW}Starting deployment...${NC}"

# Run the one-click deploy
./deploy/one-click-deploy.sh

echo -e "${GREEN}Done! Your app should be deploying now.${NC}"