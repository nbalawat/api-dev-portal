#!/bin/bash
# Quick setup script for GCP deployment prerequisites

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== GCP Deployment Quick Setup ===${NC}"
echo ""

# Check if service account file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide path to service account JSON file${NC}"
    echo "Usage: ./quick-setup.sh path/to/service-account.json YOUR_PROJECT_ID"
    exit 1
fi

if [ -z "$2" ]; then
    echo -e "${RED}Error: Please provide your GCP project ID${NC}"
    echo "Usage: ./quick-setup.sh path/to/service-account.json YOUR_PROJECT_ID"
    exit 1
fi

SERVICE_ACCOUNT_FILE="$1"
PROJECT_ID="$2"

# Check if service account file exists
if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo -e "${RED}Error: Service account file not found: $SERVICE_ACCOUNT_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Setting up GCP with:${NC}"
echo "  Service Account: $SERVICE_ACCOUNT_FILE"
echo "  Project ID: $PROJECT_ID"
echo ""

# Step 1: Authenticate with service account
echo -e "${YELLOW}Step 1: Authenticating with service account...${NC}"
if gcloud auth activate-service-account --key-file="$SERVICE_ACCOUNT_FILE"; then
    echo -e "${GREEN}✓ Authentication successful${NC}"
else
    echo -e "${RED}✗ Authentication failed${NC}"
    exit 1
fi

# Step 2: Set project
echo -e "${YELLOW}Step 2: Setting project...${NC}"
if gcloud config set project "$PROJECT_ID"; then
    echo -e "${GREEN}✓ Project set to $PROJECT_ID${NC}"
else
    echo -e "${RED}✗ Failed to set project${NC}"
    exit 1
fi

# Step 3: Enable required APIs
echo -e "${YELLOW}Step 3: Enabling required APIs...${NC}"
echo "This may take a minute..."

APIS=(
    "compute.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "iam.googleapis.com"
)

for api in "${APIS[@]}"; do
    echo -n "  Enabling $api... "
    if gcloud services enable "$api" --quiet 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}(already enabled or error)${NC}"
    fi
done

# Step 4: Verify setup
echo ""
echo -e "${YELLOW}Step 4: Verifying setup...${NC}"

# Check authentication
echo -n "  Checking authentication... "
if gcloud auth list --format="value(account)" | grep -q "gserviceaccount.com"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Check project
echo -n "  Checking project... "
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
    echo -e "${GREEN}✓ ($PROJECT_ID)${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Test compute API
echo -n "  Testing Compute API access... "
if gcloud compute regions list --limit=1 &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ (may need additional permissions)${NC}"
fi

# Optional: Set up application default credentials
echo ""
echo -e "${YELLOW}Optional: Setting up application default credentials...${NC}"
export GOOGLE_APPLICATION_CREDENTIALS="$SERVICE_ACCOUNT_FILE"
echo -e "${GREEN}✓ GOOGLE_APPLICATION_CREDENTIALS set${NC}"

# Summary
echo ""
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo ""
echo "You can now run the deployment with:"
echo -e "${GREEN}  ./deploy/one-click-deploy.sh${NC}"
echo ""
echo "To use this setup in future terminal sessions, run:"
echo -e "${YELLOW}  export GOOGLE_APPLICATION_CREDENTIALS=\"$SERVICE_ACCOUNT_FILE\"${NC}"
echo -e "${YELLOW}  gcloud config set project $PROJECT_ID${NC}"
echo ""

# Check for common issues
echo -e "${YELLOW}Checking for potential issues...${NC}"

# Check billing
echo -n "  Billing enabled: "
if gcloud beta billing projects describe "$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}? (couldn't verify, but may be enabled)${NC}"
fi

# Get service account email
SERVICE_ACCOUNT_EMAIL=$(gcloud config get-value account 2>/dev/null)
echo "  Service account: $SERVICE_ACCOUNT_EMAIL"

echo ""
echo -e "${GREEN}Ready to deploy!${NC}"