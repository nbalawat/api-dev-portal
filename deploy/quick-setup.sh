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

# Default service account path (hardcoded)
DEFAULT_SA_PATH="/Users/nbalawat/development/scalable-rag-pipeline-with-access-entitlements/infrastructure/service-accounts/deploy-dev-sa.json"

# Check if using environment variable or arguments
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -n "$GCP_PROJECT_ID" ]; then
    echo -e "${GREEN}Using environment variables:${NC}"
    echo "  GOOGLE_APPLICATION_CREDENTIALS: $GOOGLE_APPLICATION_CREDENTIALS"
    echo "  GCP_PROJECT_ID: $GCP_PROJECT_ID"
    SERVICE_ACCOUNT_FILE="$GOOGLE_APPLICATION_CREDENTIALS"
    PROJECT_ID="$GCP_PROJECT_ID"
elif [ -n "$1" ] && [ -n "$2" ]; then
    SERVICE_ACCOUNT_FILE="$1"
    PROJECT_ID="$2"
elif [ -f "$DEFAULT_SA_PATH" ]; then
    # Use default hardcoded path
    echo -e "${GREEN}Using default service account path${NC}"
    SERVICE_ACCOUNT_FILE="$DEFAULT_SA_PATH"
    
    # Still need project ID
    if [ -n "$1" ]; then
        PROJECT_ID="$1"
    elif [ -n "$GCP_PROJECT_ID" ]; then
        PROJECT_ID="$GCP_PROJECT_ID"
    else
        echo -e "${YELLOW}Please provide project ID:${NC}"
        echo "Usage: ./quick-setup.sh YOUR_PROJECT_ID"
        echo "Or set: export GCP_PROJECT_ID=your-project-id"
        exit 1
    fi
else
    echo -e "${RED}Error: Missing required parameters${NC}"
    echo ""
    echo "Option 1 - Use default path with project ID:"
    echo "  ./quick-setup.sh YOUR_PROJECT_ID"
    echo ""
    echo "Option 2 - Use environment variables:"
    echo "  export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json"
    echo "  export GCP_PROJECT_ID=your-project-id"
    echo "  ./quick-setup.sh"
    echo ""
    echo "Option 3 - Pass as arguments:"
    echo "  ./quick-setup.sh path/to/service-account.json YOUR_PROJECT_ID"
    exit 1
fi

# Check if service account file exists
if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo -e "${RED}Error: Service account file not found: $SERVICE_ACCOUNT_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Setting up GCP with:${NC}"
echo "  Service Account: $SERVICE_ACCOUNT_FILE"
echo "  Project ID: $PROJECT_ID"
echo ""

# Step 1: Set up authentication
echo -e "${YELLOW}Step 1: Setting up authentication...${NC}"

# Export the environment variable
export GOOGLE_APPLICATION_CREDENTIALS="$SERVICE_ACCOUNT_FILE"
echo -e "${GREEN}✓ GOOGLE_APPLICATION_CREDENTIALS set${NC}"

# Try to use application default credentials first
if gcloud auth application-default print-access-token &>/dev/null; then
    echo -e "${GREEN}✓ Using Application Default Credentials${NC}"
else
    # Fall back to service account activation
    echo "  Activating service account..."
    if gcloud auth activate-service-account --key-file="$SERVICE_ACCOUNT_FILE"; then
        echo -e "${GREEN}✓ Service account activated${NC}"
    else
        echo -e "${RED}✗ Authentication failed${NC}"
        exit 1
    fi
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

# Show environment setup for future use
echo ""
echo -e "${YELLOW}Environment Configuration:${NC}"
echo "GOOGLE_APPLICATION_CREDENTIALS is set to: $SERVICE_ACCOUNT_FILE"

# Summary
echo ""
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo ""
echo "You can now run the deployment with:"
echo -e "${GREEN}  ./deploy/one-click-deploy.sh${NC}"
echo ""
echo "To use this setup in future terminal sessions, add to your ~/.bashrc or ~/.zshrc:"
echo -e "${YELLOW}  export GOOGLE_APPLICATION_CREDENTIALS=\"$SERVICE_ACCOUNT_FILE\"${NC}"
echo -e "${YELLOW}  export GCP_PROJECT_ID=\"$PROJECT_ID\"${NC}"
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