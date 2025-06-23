#!/bin/bash
# Force cleanup script - removes ALL API Portal resources without prompting
# USE WITH CAUTION - This will delete all instances with api-portal tag

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}=== API Portal - FORCE CLEANUP (No Prompts) ===${NC}"
echo -e "${RED}⚠️  WARNING: This will delete ALL API Portal resources!${NC}"
echo ""

# Give user a chance to cancel
echo -e "${YELLOW}Starting force cleanup in 5 seconds... Press Ctrl+C to cancel${NC}"
for i in 5 4 3 2 1; do
    echo -n "$i... "
    sleep 1
done
echo ""

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
echo -e "${BLUE}Project: $PROJECT_ID${NC}"

# Delete all instances with api-portal tag
echo -e "${YELLOW}Deleting all API Portal instances...${NC}"
instances=$(gcloud compute instances list --filter="tags.items=api-portal" --format="value(name,zone)")

if [ -n "$instances" ]; then
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            instance_name=$(echo "$line" | awk '{print $1}')
            zone=$(echo "$line" | awk '{print $2}')
            
            echo -e "${YELLOW}Deleting: $instance_name in $zone${NC}"
            gcloud compute instances delete "$instance_name" --zone="$zone" --quiet || true
        fi
    done <<< "$instances"
    echo -e "${GREEN}✓ All instances deleted${NC}"
else
    echo -e "${GREEN}No instances found${NC}"
fi

# Delete firewall rules
echo -e "${YELLOW}Deleting firewall rules...${NC}"
gcloud compute firewall-rules delete allow-api-portal --quiet 2>/dev/null || true
echo -e "${GREEN}✓ Firewall rules cleaned${NC}"

echo ""
echo -e "${GREEN}=== Force cleanup complete! ===${NC}"
echo -e "${GREEN}All API Portal resources have been removed.${NC}"