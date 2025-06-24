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

You have two options:

**Option A: Use Environment Variable (Recommended)**
```bash
# Set the environment variable
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account.json"
export GCP_PROJECT_ID="YOUR_PROJECT_ID"

# The gcloud CLI will automatically use these credentials
gcloud config set project $GCP_PROJECT_ID
```

**Option B: Activate Service Account**
```bash
# Explicitly activate the service account
gcloud auth activate-service-account --key-file=path/to/your-service-account.json
gcloud config set project YOUR_PROJECT_ID
```

**Verify authentication:**
```bash
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

We provide a setup script that handles everything:

**Option 1: Using Environment Variables**
```bash
# Set your credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account.json"
export GCP_PROJECT_ID="YOUR_PROJECT_ID"

# Run the setup
./deploy/quick-setup.sh
```

**Option 2: Pass as Arguments**
```bash
./deploy/quick-setup.sh path/to/your-service-account.json YOUR_PROJECT_ID
```

The script will:
- Set up authentication (using env vars or service account activation)
- Configure your project
- Enable all required APIs
- Verify everything is working

## Using Environment Variables Throughout

For a completely environment-based setup, add these to your shell profile (~/.bashrc or ~/.zshrc):

```bash
# Add to your shell profile
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/your-service-account.json"
export GCP_PROJECT_ID="your-project-id"

# Reload your shell
source ~/.bashrc  # or source ~/.zshrc
```

Now all scripts will automatically use these credentials without any authentication steps!

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