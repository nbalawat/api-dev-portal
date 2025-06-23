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

### 3. `gcp-quick-start.md`
- **What it is**: Complete documentation with multiple deployment options
- **Includes**: Cloud Shell deployment, manual steps, troubleshooting

## Quickest Way to Deploy

```bash
# 1. Make sure you have gcloud CLI installed
# 2. Set your GCP project
gcloud config set project YOUR_PROJECT_ID

# 3. Run the one-click deploy
./deploy/one-click-deploy.sh
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

To avoid charges when you're done testing:

```bash
# Delete the VM (replace with your instance name)
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