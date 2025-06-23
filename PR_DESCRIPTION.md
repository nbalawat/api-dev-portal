# Fix marketplace proxy error in Docker environment

## Summary
- Fixed the marketplace proxy error that was occurring when running the application in Docker
- Resolved the "fetch failed" error for marketplace payment endpoints

## Problem
The frontend container was trying to reach the backend using `localhost:8000`, but inside Docker containers, `localhost` refers to the container itself, not the host machine. This caused all marketplace API calls to fail with a proxy error.

Error details:
- Status: 500 Proxy Error
- Error: "fetch failed"
- Type: "marketplace_proxy_error"

## Solution
- Added `INTERNAL_API_URL` environment variable for server-side requests in Docker
- Updated the marketplace proxy route to use the backend service name (`http://backend:8000`) when running in Docker
- Enhanced error handling to provide better debugging information for networking issues
- Added detection for common Docker networking errors (ECONNREFUSED, ENOTFOUND)

## Test Results
After applying the fix, the marketplace proxy successfully connects to the backend:
```
✅ Marketplace proxy is working correctly!
Status: 200 OK
Response Time: 49ms
```

## Changes
- Modified `frontend/src/app/api/marketplace-proxy/route.ts` to use internal Docker networking
- Updated `docker-compose.yml` to include the `INTERNAL_API_URL` environment variable

This fix ensures that the marketplace payment processing endpoints work correctly in the Docker environment.