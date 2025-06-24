# Quick Deployment Scripts

This directory contains scripts for quickly deploying the API Developer Portal to Google Cloud Platform.

## Available Scripts

### 1. `one-click-deploy.sh` (Recommended)
- **What it does**: Creates a GCP VM, installs everything, and starts your app
- **Run from**: Your local machine (with gcloud CLI installed)
- **Time**: ~5 minutes
- **Usage**: `./deploy/one-click-deploy.sh`

### 2. `quick-deploy.sh`
- **What it does**: Installs Docker, clones repo, and starts services on a VM
- **Run from**: Inside a GCP VM (as a startup script)
- **Time**: ~3 minutes after VM is created
- **Usage**: Used automatically by the one-click script or manually on a VM

### 3. `cleanup.sh`
- **What it does**: Interactive cleanup of all deployed resources
- **Run from**: Your local machine
- **Usage**: `./deploy/cleanup.sh`

### 4. `cleanup-all.sh`
- **What it does**: Force deletes all API Portal resources (no prompts)
- **Run from**: Your local machine
- **Usage**: `./deploy/cleanup-all.sh`

### 5. `gcp-quick-start.md`
- **What it is**: Complete documentation with multiple deployment options
- **Includes**: Cloud Shell deployment, manual steps, troubleshooting

## Prerequisites

### Quick Setup (With Hardcoded Service Account):
```bash
# Just provide your project ID - service account is already configured
./deploy/quick-setup.sh YOUR_PROJECT_ID
```

### Or source the deployment config:
```bash
# Load the preconfigured service account path
source deploy/.env.deploy

# Set your project ID
export GCP_PROJECT_ID="your-project-id"

# Run setup
./deploy/quick-setup.sh
```

The service account path is hardcoded to:
`/Users/nbalawat/development/scalable-rag-pipeline-with-access-entitlements/infrastructure/service-accounts/deploy-dev-sa.json`

See `PREREQUISITES.md` for other authentication options.

## Quickest Way to Deploy

```bash
# If you've set GOOGLE_APPLICATION_CREDENTIALS, just run:
./deploy/one-click-deploy.sh

# The script will use your environment credentials automatically!
```

That's it! The script will:
- Create a VM instance
- Install Docker and Docker Compose
- Clone your repository
- Start all services (Frontend, Backend, PostgreSQL, Redis)
- Open firewall ports
- Give you the URLs to access your app

## What You'll Get

After deployment, you'll have:
- Frontend: `http://[VM-IP]:3000`
- Backend API: `http://[VM-IP]:8000`
- API Docs: `http://[VM-IP]:8000/docs`

## Clean Up

We provide cleanup scripts to easily remove all deployed resources:

### Option 1: Interactive Cleanup (Recommended)
```bash
./deploy/cleanup.sh
```
This will:
- Find all API Portal instances
- Let you choose what to delete
- Remove firewall rules
- Show you what's left

### Option 2: Force Cleanup (Delete Everything)
```bash
./deploy/cleanup-all.sh
```
This will:
- Delete ALL instances with `api-portal` tag
- Remove all firewall rules
- No prompts (use with caution!)

### Option 3: Manual Cleanup
```bash
# Delete specific VM
gcloud compute instances delete api-portal-demo-TIMESTAMP --zone=us-central1-a

# Delete firewall rule
gcloud compute firewall-rules delete allow-api-portal
```

## Notes

- These scripts are for **quick testing/demo purposes only**
- For production, use Cloud Run, GKE, or properly configured VMs
- Default passwords are auto-generated but still demo-quality
- The VM costs about $24-48/month if left running

## Troubleshooting

If something goes wrong:

1. Check the startup script logs:
   ```bash
   gcloud compute ssh INSTANCE_NAME --zone=us-central1-a
   sudo cat /var/log/startup-script.log
   ```

2. Check Docker services:
   ```bash
   cd ~/api-developer-portal
   docker-compose ps
   docker-compose logs
   ```

3. Make sure ports 3000 and 8000 are open in the firewall