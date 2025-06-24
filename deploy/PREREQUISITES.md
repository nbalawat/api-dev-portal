# GCP Deployment Prerequisites

## What You Already Have ✓
- Google Cloud Project
- Service Account JSON file

## What You Need to Set Up

### 1. Install gcloud CLI
The deployment scripts use `gcloud` commands. Install it based on your OS:

**macOS:**
```bash
# Using Homebrew
brew install --cask google-cloud-sdk

# Or download from Google
curl https://sdk.cloud.google.com | bash
```

**Linux/WSL:**
```bash
curl https://sdk.cloud.google.com | bash
```

**Windows:**
Download the installer from: https://cloud.google.com/sdk/docs/install

### 2. Authenticate with Your Service Account

```bash
# Set up authentication with your service account
gcloud auth activate-service-account --key-file=path/to/your-service-account.json

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Verify authentication
gcloud auth list
gcloud config list
```

### 3. Enable Required APIs
Run this command to enable all necessary APIs:

```bash
# Enable required APIs
gcloud services enable \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com
```

### 4. Check Service Account Permissions
Your service account needs these roles:
- `Compute Instance Admin` (roles/compute.instanceAdmin)
- `Security Admin` (roles/compute.securityAdmin) - for firewall rules
- `Service Account User` (roles/iam.serviceAccountUser)

To add these roles:
```bash
# Replace YOUR_SERVICE_ACCOUNT_EMAIL with your service account email
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/compute.instanceAdmin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/compute.securityAdmin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/iam.serviceAccountUser"
```

### 5. Check Quotas (Optional)
Make sure you have quota for:
- 1 VM instance (e2-medium)
- 1 external IP address
- 30GB of persistent disk

Check quotas:
```bash
gcloud compute project-info describe --project=YOUR_PROJECT_ID
```

### 6. Billing
Ensure billing is enabled on your project. The deployment will cost approximately:
- **VM (e2-medium)**: ~$24-48/month if left running
- **Storage**: ~$1-2/month
- **Network**: Minimal unless high traffic

## Quick Setup Script

Save this as `setup-gcp.sh` and run it:

```bash
#!/bin/bash
# Quick GCP setup script

# Authenticate with service account
echo "Authenticating with service account..."
gcloud auth activate-service-account --key-file=path/to/your-service-account.json

# Set project
echo "Setting project..."
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
echo "Enabling required APIs..."
gcloud services enable \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com

# Check authentication
echo "Current authenticated account:"
gcloud auth list

echo "Setup complete! You can now run ./deploy/one-click-deploy.sh"
```

## Alternative: Use Default Application Credentials

If you prefer not to use the service account JSON directly:

```bash
# Set the environment variable
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account.json"

# Then use application default credentials
gcloud auth application-default login
```

## Verify Everything is Ready

Run this command to verify your setup:

```bash
# Check you're authenticated
gcloud auth list

# Check your project is set
gcloud config get-value project

# Test creating a firewall rule (then delete it)
gcloud compute firewall-rules create test-rule --allow tcp:80 --quiet
gcloud compute firewall-rules delete test-rule --quiet

# If all commands work, you're ready!
```

## Ready to Deploy!

Once everything above is set up, you can deploy with:

```bash
./deploy/one-click-deploy.sh
```

## Troubleshooting

### "Permission Denied" Errors
Your service account might need additional permissions. Try adding:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/editor"
```

### API Not Enabled Errors
Enable the specific API mentioned in the error:
```bash
gcloud services enable [API_NAME]
```

### Quota Errors
Check your quotas and request increases if needed:
- Go to: https://console.cloud.google.com/iam-admin/quotas
- Filter by "Compute Engine API"
- Request quota increase if needed