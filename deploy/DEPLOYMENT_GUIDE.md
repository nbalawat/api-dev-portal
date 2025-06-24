# API Developer Portal - GCP Deployment Guide

## Quick Start

### Prerequisites
- Google Cloud SDK (`gcloud`) installed
- Service account JSON with appropriate permissions
- Git repository (public or with SSH access configured)

### Deployment Scripts

#### 1. Optimized Deployment (Recommended)
```bash
./deploy/optimized-deploy.sh
```
- Uses `docker-compose.prod.yml` without profiles
- Faster deployment with better error handling
- Builds frontend synchronously for reliability

#### 2. One-Click Deployment
```bash
./deploy/one-click-deploy.sh
```
- Original deployment script
- Builds frontend in background
- May require manual frontend fix

#### 3. Manual Deployment
```bash
./deploy/manual-deploy.sh INSTANCE_NAME
```
- Deploy code updates to existing instance
- Preserves existing data

### Troubleshooting

#### Frontend Not Running?
If the frontend container isn't running after deployment:

```bash
./deploy/fix-frontend.sh INSTANCE_NAME
```

Example:
```bash
./deploy/fix-frontend.sh api-portal-demo-1750729992
```

#### Check Service Status
```bash
gcloud compute ssh INSTANCE_NAME --zone=us-central1-a --command='cd ~/api-developer-portal && sudo docker-compose ps'
```

#### Monitor Frontend Build
```bash
gcloud compute ssh INSTANCE_NAME --zone=us-central1-a --command='cd ~/api-developer-portal && sudo docker-compose logs -f frontend'
```

### Cleanup

#### Interactive Cleanup
```bash
./deploy/cleanup.sh
```

#### Force Cleanup All
```bash
./deploy/cleanup-all.sh
```

## Known Issues & Solutions

### Issue: Frontend container not starting
**Cause**: Docker Compose profiles require explicit activation
**Solution**: 
1. Use `optimized-deploy.sh` which uses `docker-compose.prod.yml` without profiles
2. Or run `fix-frontend.sh` on existing deployments

### Issue: npm install takes too long
**Cause**: Building node modules from scratch on small VMs
**Solution**: 
- The scripts now build frontend synchronously
- Consider using larger machine types for faster builds

### Issue: Missing .env.dev file
**Cause**: Backend expects .env.dev but only .env is created
**Solution**: Scripts now automatically copy .env to .env.dev

## Environment Variables

The deployment scripts automatically set up:
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL` for backend connection
- `REDIS_URL` for Redis connection
- `SECRET_KEY` and `JWT_SECRET_KEY` for security

## Security Notes

- Default deployment uses demo passwords
- Firewall rules allow public access to ports 3000 and 8000
- For production, update passwords and restrict access

## Deployment Architecture

```
┌─────────────────┐
│   GCP VM        │
│                 │
│  ┌───────────┐  │
│  │  Docker   │  │
│  │           │  │
│  │ ┌───────┐ │  │ :3000
│  │ │Frontend│ │  │◄─────
│  │ └───────┘ │  │
│  │           │  │
│  │ ┌───────┐ │  │ :8000
│  │ │Backend │ │  │◄─────
│  │ └───────┘ │  │
│  │           │  │
│  │ ┌───────┐ │  │
│  │ │Postgres│ │  │ :5433
│  │ └───────┘ │  │
│  │           │  │
│  │ ┌───────┐ │  │
│  │ │ Redis  │ │  │ :6380
│  │ └───────┘ │  │
│  └───────────┘  │
└─────────────────┘
```

## Tips

1. **Monitor deployment**: Always use the monitoring option when deploying
2. **Check logs**: Use `/var/log/startup-script.log` for deployment issues
3. **Frontend build**: Takes 3-5 minutes, be patient
4. **Service health**: Backend should be healthy before frontend starts

## Support

For issues:
1. Check the deployment logs
2. Verify all containers are running
3. Check Docker logs for specific services
4. Ensure the repository is accessible (public or SSH configured)