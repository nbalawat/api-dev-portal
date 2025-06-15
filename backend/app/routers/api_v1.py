"""
API v1 Router - Protected endpoints that require API key authentication.

This router demonstrates how to use API key authentication for protected endpoints.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies.database import get_database
from ..middleware import get_current_api_key, require_api_key, require_api_key_scopes
from ..middleware.permissions import (
    require_resource_permission, require_resource_access, require_resource_write,
    get_permission_checker, PermissionChecker
)
from ..core.permissions import ResourceType, Permission
from ..models.api_key import APIKey, APIKeyScope
from ..models.user import User, UserResponse
from ..core.api_keys import APIKeyManager

router = APIRouter(prefix="/api/v1")


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    api_key: APIKey = Depends(require_resource_access(ResourceType.USER)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get the profile of the user who owns the API key.
    
    Requires 'read' scope.
    """
    # Get the user associated with this API key
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.get("/api-key/info")
async def get_api_key_info(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get information about the current API key.
    
    Returns basic info about the API key being used for authentication.
    """
    return {
        "key_id": api_key.key_id,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "rate_limit": api_key.rate_limit,
        "rate_limit_period": api_key.rate_limit_period,
        "total_requests": api_key.total_requests,
        "requests_today": api_key.requests_today,
        "last_used_at": api_key.last_used_at,
        "expires_at": api_key.expires_at
    }


@router.get("/api-key/usage-stats")
async def get_api_key_usage_stats(
    api_key: APIKey = Depends(require_resource_access(ResourceType.ANALYTICS)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get usage statistics for the current API key.
    
    Requires 'analytics' scope.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select, func, and_
    from ..models.api_key import APIKeyUsage
    
    # Calculate time windows
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    # Get usage statistics
    usage_query = select(APIKeyUsage).where(
        and_(
            APIKeyUsage.api_key_id == api_key.id,
            APIKeyUsage.timestamp >= month_start
        )
    )
    usage_result = await db.execute(usage_query)
    usage_records = usage_result.scalars().all()
    
    # Calculate metrics
    total_requests = len(usage_records)
    requests_today = len([r for r in usage_records if r.timestamp >= today_start])
    requests_this_week = len([r for r in usage_records if r.timestamp >= week_start])
    
    # Response time analysis
    response_times = [r.response_time_ms for r in usage_records if r.response_time_ms]
    avg_response_time = sum(response_times) / len(response_times) if response_times else None
    
    # Error rate analysis
    error_count = len([r for r in usage_records if r.status_code >= 400])
    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "api_key_id": api_key.id,
        "total_requests": total_requests,
        "requests_today": requests_today,
        "requests_this_week": requests_this_week,
        "average_response_time_ms": avg_response_time,
        "error_rate_percent": error_rate,
        "rate_limit_remaining": await APIKeyManager.check_rate_limit(db, api_key)
    }


@router.post("/test-endpoint")
async def test_write_endpoint(
    data: dict,
    api_key: APIKey = Depends(require_resource_write(ResourceType.USER))
):
    """
    Test endpoint that requires write permissions.
    
    Requires 'write' scope.
    """
    return {
        "message": "Write operation successful",
        "api_key_id": api_key.key_id,
        "data_received": data,
        "timestamp": api_key.last_used_at
    }


@router.get("/admin/system-info")
async def get_system_info(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ))
):
    """
    Admin endpoint that returns system information.
    
    Requires 'admin' scope.
    """
    import sys
    from datetime import datetime
    
    return {
        "message": "System information (admin access)",
        "api_key_id": api_key.key_id,
        "system": {
            "python_version": sys.version,
            "timestamp": datetime.utcnow()
        }
    }


@router.get("/rate-limit-test")
async def rate_limit_test(
    request: Request,
    api_key: APIKey = Depends(require_api_key)
):
    """
    Test endpoint to demonstrate rate limiting.
    
    This endpoint can be called to test rate limits for your API key.
    Response includes rate limit headers showing current status.
    """
    return {
        "message": "Rate limit test successful",
        "api_key_id": api_key.key_id,
        "rate_limit_config": {
            "limit": api_key.rate_limit,
            "period": api_key.rate_limit_period.value if api_key.rate_limit_period else None
        },
        "usage_counters": {
            "total_requests": api_key.total_requests,
            "requests_today": api_key.requests_today
        },
        "request_info": {
            "method": request.method,
            "path": request.url.path,
            "ip": request.client.host if request.client else "unknown",
            "timestamp": datetime.utcnow().isoformat()
        },
        "rate_limit_headers": {
            "note": "Check response headers for X-RateLimit-* values",
            "headers": [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining", 
                "X-RateLimit-Reset",
                "X-RateLimit-Algorithm"
            ]
        }
    }


@router.get("/rate-limit/burst-test")
async def burst_test_endpoint(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Expensive endpoint for testing burst rate limiting.
    
    This endpoint has a high request cost to test rate limiting
    behavior under heavy usage scenarios.
    """
    import time
    time.sleep(0.1)  # Simulate some processing time
    
    return {
        "message": "Burst test completed",
        "api_key_id": api_key.key_id,
        "note": "This endpoint has higher rate limit cost",
        "processing_time": "100ms",
        "request_cost": "High (simulates expensive operation)"
    }


@router.post("/rate-limit/heavy-operation")
async def heavy_operation_endpoint(
    data: dict,
    api_key: APIKey = Depends(require_resource_write(ResourceType.USER))
):
    """
    Heavy operation endpoint with high rate limit cost.
    
    Demonstrates how different operations can have different
    rate limiting costs based on their computational expense.
    """
    import time
    time.sleep(0.2)  # Simulate heavy processing
    
    return {
        "message": "Heavy operation completed",
        "api_key_id": api_key.key_id,
        "data_processed": len(str(data)),
        "operation_type": "write",
        "processing_time": "200ms",
        "rate_limit_cost": "Very High (5x normal request)",
        "processed_data": data
    }


@router.get("/analytics/realtime")
async def get_realtime_analytics(
    api_key: APIKey = Depends(require_resource_access(ResourceType.ANALYTICS))
):
    """
    Get real-time analytics and usage metrics.
    
    Shows live system performance and usage statistics.
    """
    from ..services.usage_tracking import get_usage_tracker
    
    tracker = get_usage_tracker()
    metrics = tracker.get_realtime_metrics()
    
    return {
        "message": "Real-time analytics data",
        "api_key_id": api_key.key_id,
        "metrics": metrics,
        "note": "This shows live system performance metrics"
    }


@router.get("/analytics/my-usage")
async def get_my_usage_analytics(
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    api_key: APIKey = Depends(require_resource_access(ResourceType.ANALYTICS))
):
    """
    Get detailed usage analytics for the current API key.
    
    Returns comprehensive metrics including request patterns,
    response times, and error rates.
    """
    from ..services.usage_tracking import get_usage_tracker
    
    tracker = get_usage_tracker()
    metrics = await tracker.get_api_key_metrics(str(api_key.id), hours)
    
    return {
        "message": "API key usage analytics",
        "api_key_info": {
            "key_id": api_key.key_id,
            "name": api_key.name,
            "scopes": api_key.scopes
        },
        "analytics": metrics
    }


@router.get("/lifecycle/check")
async def check_lifecycle_status(
    api_key: APIKey = Depends(require_resource_access(ResourceType.API_KEY))
):
    """
    Check lifecycle status of the current API key.
    
    Returns information about expiration, rotation schedule, and recommendations.
    """
    from ..core.key_lifecycle import APIKeyLifecycleManager
    
    manager = APIKeyLifecycleManager()
    lifecycle_status = await manager.get_lifecycle_status(str(api_key.id))
    
    return {
        "message": "API key lifecycle status",
        "api_key_id": api_key.key_id,
        "lifecycle": lifecycle_status,
        "quick_actions": {
            "rotate_now": f"/lifecycle/rotate/{api_key.id}",
            "setup_auto_rotation": f"/lifecycle/auto-rotation/{api_key.id}",
            "set_expiration": f"/lifecycle/expiration/{api_key.id}"
        }
    }


@router.post("/lifecycle/quick-rotate")
async def quick_rotate_key(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.UPDATE))
):
    """
    Quick rotation of the current API key.
    
    Performs immediate rotation with default settings for convenience.
    """
    from ..core.key_lifecycle import APIKeyLifecycleManager, RotationTrigger
    
    manager = APIKeyLifecycleManager()
    rotation_result = await manager.rotate_api_key(
        api_key_id=str(api_key.id),
        trigger=RotationTrigger.MANUAL,
        user_id=str(api_key.user_id),
        preserve_settings=True
    )
    
    if rotation_result.success:
        return {
            "message": "API key rotated successfully",
            "old_key_id": rotation_result.old_key_id,
            "new_key_id": rotation_result.new_key_id,
            "new_secret_key": rotation_result.new_secret_key,
            "transition_period_days": rotation_result.transition_period_days,
            "important_note": "Store the new secret key securely - it won't be shown again",
            "next_steps": [
                "Update your applications with the new API key",
                "Test the new key before the transition period ends",
                "The old key will be deactivated automatically"
            ]
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rotation failed: {rotation_result.message}"
        )


@router.get("/permissions/check")
async def check_my_permissions(
    checker: PermissionChecker = Depends(get_permission_checker)
):
    """
    Get detailed permission information for the current API key.
    
    Shows all permissions, capabilities, and access levels.
    """
    return {
        "api_key_id": checker.api_key.key_id,
        "scopes": checker.api_key.scopes,
        "all_permissions": checker.get_all_permissions(),
        "resource_permissions": {
            "user": checker.get_resource_permissions(ResourceType.USER),
            "api_key": checker.get_resource_permissions(ResourceType.API_KEY),
            "analytics": checker.get_resource_permissions(ResourceType.ANALYTICS),
            "admin": checker.get_resource_permissions(ResourceType.ADMIN),
            "system": checker.get_resource_permissions(ResourceType.SYSTEM)
        },
        "capabilities": {
            "is_admin": checker.is_admin(),
            "can_view_analytics": checker.can_view_analytics(),
            "can_export_data": checker.can_export_data(),
            "can_access_own_data": checker.can_access_user_data(str(checker.api_key.user_id)),
            "can_manage_all_users": checker.can(ResourceType.USER, Permission.MANAGE),
            "can_manage_all_api_keys": checker.can(ResourceType.API_KEY, Permission.MANAGE)
        }
    }


@router.get("/users/list")
async def list_users(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.USER, Permission.LIST)),
    checker: PermissionChecker = Depends(get_permission_checker),
    db: AsyncSession = Depends(get_database)
):
    """
    List users (requires user:list permission).
    
    Demonstrates resource-specific permission checking.
    """
    from sqlalchemy import select
    
    # Check if can manage all users or just view own data
    if checker.can(ResourceType.USER, Permission.MANAGE):
        # Admin can see all users
        result = await db.execute(select(User).limit(10))
        users = result.scalars().all()
        message = "Admin access: showing all users"
    else:
        # Regular user can only see their own data
        result = await db.execute(select(User).where(User.id == api_key.user_id))
        users = result.scalars().all()
        message = "Regular access: showing only your user data"
    
    return {
        "message": message,
        "users": [UserResponse.from_orm(user) for user in users],
        "permissions_used": "user:list",
        "total_found": len(users)
    }


@router.post("/analytics/export")
async def export_analytics_data(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.EXPORT)),
    format: str = "json"
):
    """
    Export analytics data (requires analytics:export permission).
    
    Demonstrates fine-grained permission requirements.
    """
    # This would implement actual data export
    return {
        "message": "Analytics export initiated",
        "api_key_id": api_key.key_id,
        "export_format": format,
        "permissions_used": "analytics:export",
        "note": "This would return actual exported data in a real implementation"
    }


@router.post("/admin/manage-system")
async def manage_system_settings(
    settings: dict,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.SYSTEM, Permission.CONFIGURE))
):
    """
    Manage system settings (requires system:configure permission).
    
    Demonstrates admin-level system configuration access.
    """
    return {
        "message": "System configuration updated",
        "api_key_id": api_key.key_id,
        "settings_received": settings,
        "permissions_used": "system:configure",
        "note": "This would apply actual system configuration changes"
    }


@router.get("/public-endpoint")
async def public_endpoint():
    """
    Public endpoint that doesn't require authentication.
    
    This endpoint is accessible without an API key for testing.
    Note: This endpoint won't be protected by the middleware since
    it's not under a protected path pattern.
    """
    return {
        "message": "This is a public endpoint",
        "authentication_required": False,
        "timestamp": "2024-01-01T00:00:00Z"
    }