#!/bin/bash
# Cleanup script for GCP API Portal deployment
# This script helps you remove all resources created by the deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== API Developer Portal - GCP Cleanup Script ===${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No GCP project set${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${YELLOW}Current project: $PROJECT_ID${NC}"
echo ""

# Function to list instances with our tag
list_portal_instances() {
    echo -e "${YELLOW}Searching for API Portal instances...${NC}"
    instances=$(gcloud compute instances list --filter="tags.items=api-portal" --format="table(name,zone,status,EXTERNAL_IP)" 2>/dev/null)
    
    if [ -z "$instances" ] || [ "$(echo "$instances" | wc -l)" -le 1 ]; then
        echo -e "${GREEN}No API Portal instances found.${NC}"
        return 1
    else
        echo -e "${GREEN}Found API Portal instances:${NC}"
        echo "$instances"
        return 0
    fi
}

# Function to delete a specific instance
delete_instance() {
    local instance_name=$1
    local zone=$2
    
    echo -e "${YELLOW}Deleting instance: $instance_name in zone: $zone${NC}"
    
    if gcloud compute instances delete "$instance_name" --zone="$zone" --quiet; then
        echo -e "${GREEN}✓ Instance $instance_name deleted successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to delete instance $instance_name${NC}"
        return 1
    fi
}

# Function to check and delete firewall rules
cleanup_firewall_rules() {
    echo -e "${YELLOW}Checking for API Portal firewall rules...${NC}"
    
    if gcloud compute firewall-rules describe allow-api-portal &>/dev/null; then
        echo -e "${YELLOW}Found firewall rule: allow-api-portal${NC}"
        
        if gcloud compute firewall-rules delete allow-api-portal --quiet; then
            echo -e "${GREEN}✓ Firewall rule deleted successfully${NC}"
        else
            echo -e "${RED}✗ Failed to delete firewall rule${NC}"
        fi
    else
        echo -e "${GREEN}No API Portal firewall rules found.${NC}"
    fi
}

# Main cleanup process
echo -e "${BLUE}Starting cleanup process...${NC}"
echo ""

# Step 1: Find all instances
if list_portal_instances; then
    echo ""
    echo -e "${YELLOW}Do you want to delete ALL API Portal instances? (y/n)${NC}"
    read -p "Delete all? " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Get all instances with api-portal tag
        instances=$(gcloud compute instances list --filter="tags.items=api-portal" --format="value(name,zone)")
        
        # Delete each instance
        while IFS= read -r line; do
            if [ -n "$line" ]; then
                instance_name=$(echo "$line" | awk '{print $1}')
                zone=$(echo "$line" | awk '{print $2}')
                delete_instance "$instance_name" "$zone"
            fi
        done <<< "$instances"
    else
        # Interactive deletion
        echo -e "${YELLOW}Enter the instance name to delete (or 'skip' to continue):${NC}"
        read -p "Instance name: " instance_name
        
        if [ "$instance_name" != "skip" ] && [ -n "$instance_name" ]; then
            # Get zone for the instance
            zone=$(gcloud compute instances list --filter="name=$instance_name" --format="value(zone)")
            
            if [ -n "$zone" ]; then
                delete_instance "$instance_name" "$zone"
            else
                echo -e "${RED}Instance $instance_name not found${NC}"
            fi
        fi
    fi
fi

echo ""

# Step 2: Cleanup firewall rules
cleanup_firewall_rules

echo ""

# Step 3: Check for any remaining resources
echo -e "${BLUE}Checking for any remaining resources...${NC}"

# Check for any instances that might have been created without tags
echo -e "${YELLOW}Recent instances (last 24 hours):${NC}"
recent_instances=$(gcloud compute instances list --format="table(name,zone,creationTimestamp)" --filter="creationTimestamp>=$(date -d '24 hours ago' '+%Y-%m-%d')" 2>/dev/null || echo "")

if [ -n "$recent_instances" ] && [ "$(echo "$recent_instances" | wc -l)" -gt 1 ]; then
    echo "$recent_instances"
    echo ""
    echo -e "${YELLOW}Note: These instances were created recently. Check if any belong to API Portal.${NC}"
else
    echo -e "${GREEN}No recent instances found.${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}=== Cleanup Summary ===${NC}"
echo ""

# Check what's left
remaining_instances=$(gcloud compute instances list --filter="tags.items=api-portal" --format="value(name)" 2>/dev/null || echo "")
remaining_firewall=$(gcloud compute firewall-rules list --filter="name=allow-api-portal" --format="value(name)" 2>/dev/null || echo "")

if [ -z "$remaining_instances" ] && [ -z "$remaining_firewall" ]; then
    echo -e "${GREEN}✓ All API Portal resources have been cleaned up!${NC}"
    echo -e "${GREEN}✓ No charges will be incurred from these resources.${NC}"
else
    echo -e "${YELLOW}⚠ Some resources may still exist:${NC}"
    
    if [ -n "$remaining_instances" ]; then
        echo -e "${RED}  - Instances still running: $remaining_instances${NC}"
    fi
    
    if [ -n "$remaining_firewall" ]; then
        echo -e "${RED}  - Firewall rules still exist: $remaining_firewall${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}Run this script again to remove remaining resources.${NC}"
fi

echo ""
echo -e "${BLUE}Cleanup complete!${NC}"

# Optional: Show estimated savings
echo ""
echo -e "${GREEN}💰 Estimated savings: ~\$24-48/month per instance${NC}"