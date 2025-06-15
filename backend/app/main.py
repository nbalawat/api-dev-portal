"""
FastAPI Developer Portal - Main Application
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import time
import uvicorn
from pathlib import Path
import os

from .core.config import settings
from .core.database import init_database, init_db, close_db
from .routers import auth, users, api_keys, api_v1, permissions, rate_limits, analytics, key_lifecycle, ui, management, activity_logs
from .middleware import APIKeyAuthMiddleware
from .middleware.rate_limiting import RateLimitMiddleware, get_rate_limit_manager

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive developer portal backend with FastAPI",
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url,
)

# CORS middleware - Enhanced for frontend integration
cors_origins = settings.cors_origins or [
    "http://localhost:3000",  # Next.js default dev server
    "http://localhost:3001",  # Alternative frontend port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Add production frontend URL if configured
if hasattr(settings, 'frontend_url') and settings.frontend_url:
    cors_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["X-Process-Time", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# API Key Authentication Middleware
app.add_middleware(
    APIKeyAuthMiddleware,
    enable_for_paths=["/api/v1/"]  # Enable API key auth for API v1 endpoints
)

# Rate Limiting Middleware (applied after API key auth)
app.add_middleware(
    RateLimitMiddleware,
    rate_limit_manager=get_rate_limit_manager(),
    enable_global_limits=True,
    enable_endpoint_limits=True
)

# Static file serving for frontend assets
FRONTEND_BUILD_PATH = Path(__file__).parent.parent.parent / "frontend" / "dist"
FRONTEND_BUILD_PATH_ALT = Path(__file__).parent.parent.parent / "frontend" / "out"  # Next.js export
FRONTEND_BUILD_PATH_BUILD = Path(__file__).parent.parent.parent / "frontend" / "build"  # Create React App

# Try to find frontend build directory
frontend_path = None
for path in [FRONTEND_BUILD_PATH, FRONTEND_BUILD_PATH_ALT, FRONTEND_BUILD_PATH_BUILD]:
    if path.exists() and path.is_dir():
        frontend_path = path
        break

if frontend_path:
    # Mount static files for frontend assets
    app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="static")
    app.mount("/_next", StaticFiles(directory=frontend_path / "_next"), name="nextjs")
    
    print(f"✅ Serving frontend from: {frontend_path}")
else:
    print("⚠️  Frontend build not found. Run 'npm run build' in frontend directory.")

# Include API routers
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(api_keys.router, prefix="/api", tags=["API Keys"])
app.include_router(api_v1.router, tags=["API v1"])
app.include_router(permissions.router, prefix="/api", tags=["Permissions"])
app.include_router(rate_limits.router, prefix="/api", tags=["Rate Limits"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(key_lifecycle.router, prefix="/api", tags=["Key Lifecycle"])
app.include_router(ui.router, prefix="/api", tags=["UI"])
app.include_router(management.router, prefix="/api", tags=["Management"])
app.include_router(activity_logs.router, prefix="/api", tags=["Activity Logs"])

# Basic middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for container monitoring
    """
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "version": settings.app_version,
        "timestamp": time.time()
    }

# Frontend SPA catch-all route
@app.get("/app/{path:path}")
@app.get("/dashboard/{path:path}")
@app.get("/admin/{path:path}")
@app.get("/auth/{path:path}")
async def serve_frontend(path: str = ""):
    """
    Serve the frontend SPA for all frontend routes
    """
    if frontend_path and (frontend_path / "index.html").exists():
        return FileResponse(frontend_path / "index.html")
    else:
        return JSONResponse(
            status_code=404,
            content={"detail": "Frontend not available. Please build the frontend first."}
        )

# Root endpoint - serve frontend or API info
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - serves frontend if available, otherwise API information
    """
    # If frontend is available and request accepts HTML, serve the frontend
    if frontend_path and (frontend_path / "index.html").exists():
        return FileResponse(frontend_path / "index.html")
    
    # Otherwise return API information
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.app_env,
        "docs_url": settings.docs_url or "Documentation disabled in production",
        "health_check": "/health",
        "frontend_available": frontend_path is not None
    }

# Basic info endpoint
@app.get("/info", tags=["Info"])
async def info():
    """
    API information endpoint
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "debug": settings.debug,
        "features": [
            "Authentication & Authorization",
            "User Management",
            "API Key Management", 
            "Usage Analytics",
            "Interactive Documentation",
            "Rate Limiting",
            "Admin Dashboard",
            "UI Management Interface",
            "Advanced Management Operations",
            "Key Lifecycle Management",
            "Real-time Monitoring",
            "Activity Logging & Security Monitoring"
        ]
    }

# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    print(f"🚀 {settings.app_name} v{settings.app_version} starting up...")
    print(f"📝 Environment: {settings.app_env}")
    print(f"🔧 Debug mode: {settings.debug}")
    if settings.debug:
        print(f"📚 API Documentation: http://localhost:8000/docs")
        print(f"📖 ReDoc Documentation: http://localhost:8000/redoc")
    
    # Initialize database connection
    try:
        init_database()
        print("✅ Database connection initialized successfully")
        
        # Initialize database tables
        await init_db()
        print("✅ Database tables initialized successfully")
        
        # Start usage tracking service
        from .services.usage_tracking import start_usage_tracking
        await start_usage_tracking()
        print("✅ Usage tracking service started")
        
        # Start key lifecycle service
        from .core.key_lifecycle import start_lifecycle_service
        await start_lifecycle_service()
        print("✅ Key lifecycle service started")
        
        # Start activity logging service
        from .services.activity_logging import start_activity_logging
        await start_activity_logging()
        print("✅ Activity logging service started")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print(f"⛔ {settings.app_name} shutting down...")
    
    # Stop usage tracking service
    from .services.usage_tracking import stop_usage_tracking
    await stop_usage_tracking()
    print("✅ Usage tracking service stopped")
    
    # Stop key lifecycle service
    from .core.key_lifecycle import stop_lifecycle_service
    await stop_lifecycle_service()
    print("✅ Key lifecycle service stopped")
    
    # Stop activity logging service
    from .services.activity_logging import stop_activity_logging
    await stop_activity_logging()
    print("✅ Activity logging service stopped")
    
    await close_db()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )