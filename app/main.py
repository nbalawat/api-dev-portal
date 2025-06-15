"""
FastAPI Developer Portal - Main Application
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import uvicorn

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

# CORS middleware
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
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

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(api_v1.router)
app.include_router(permissions.router)
app.include_router(rate_limits.router)
app.include_router(analytics.router)
app.include_router(key_lifecycle.router)
app.include_router(ui.router)
app.include_router(management.router)
app.include_router(activity_logs.router)

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

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with basic API information
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.app_env,
        "docs_url": settings.docs_url or "Documentation disabled in production",
        "health_check": "/health"
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