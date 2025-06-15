"""
UI Management Router

Frontend-optimized API endpoints for building modern web dashboards
and user interfaces for API key management and system monitoring.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from ..middleware.permissions import require_resource_permission, get_permission_checker, PermissionChecker
from ..middleware import require_api_key
from ..core.permissions import ResourceType, Permission
from ..models.api_key import APIKey, APIKeyStatus, APIKeyScope
from ..models.user import User
from ..dependencies.database import get_database
from ..dependencies.auth import get_current_user
from ..core.analytics import APIUsageAnalytics, AnalyticsTimeframe, AnalyticsFilter
from ..core.key_lifecycle import APIKeyLifecycleManager
from ..services.usage_tracking import get_usage_tracker


router = APIRouter(prefix="/ui")


# Response Models for UI
class DashboardStats(BaseModel):
    """Dashboard statistics model."""
    total_api_keys: int
    active_keys: int
    expiring_soon: int
    total_requests_today: int
    error_rate_today: float
    avg_response_time: float
    top_endpoint: Optional[str]
    last_activity: Optional[str]


class APIKeyCard(BaseModel):
    """API key card model for list views."""
    id: str
    key_id: str
    name: str
    status: str
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    days_until_expiry: Optional[int]
    scopes: List[str]
    lifecycle_status: str
    usage_today: int
    error_rate: float
    recommendations: List[str]


class QuickActions(BaseModel):
    """Quick actions available for UI."""
    can_create: bool
    can_rotate: bool
    can_delete: bool
    can_view_analytics: bool
    can_manage_all: bool
    suggestions: List[str]


class SystemHealth(BaseModel):
    """System health indicators for UI."""
    status: str  # healthy, warning, critical
    uptime_hours: float
    total_requests: int
    error_rate: float
    response_time: float
    active_keys: int
    recent_alerts: List[str]


class UINotification(BaseModel):
    """UI notification model."""
    id: str
    type: str  # info, warning, error, success
    title: str
    message: str
    action_url: Optional[str]
    action_text: Optional[str]
    created_at: str
    read: bool


# Dashboard endpoints
# Legacy API key-authenticated dashboard endpoint (deprecated)
@router.get("/dashboard", response_model=DashboardStats, deprecated=True, tags=["UI - Legacy"])
async def get_dashboard_stats_legacy(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get dashboard statistics (API key auth) - DEPRECATED. Use /frontend/dashboard instead.
    """
    # Implementation simplified - redirect to frontend version behavior
    checker = PermissionChecker(api_key)
    
    # Get user's API keys
    keys_query = select(APIKey).where(APIKey.user_id == api_key.user_id)
    keys_result = await db.execute(keys_query)
    user_keys = keys_result.scalars().all()
    
    # Calculate basic stats
    total_keys = len(user_keys)
    active_keys = len([k for k in user_keys if k.status == APIKeyStatus.active])
    
    # Check for expiring keys
    now = datetime.utcnow()
    expiring_soon = len([
        k for k in user_keys 
        if k.expires_at and (k.expires_at - now).days <= 30
    ])
    
    # Get usage analytics
    analytics = APIUsageAnalytics(db)
    filters = AnalyticsFilter(api_key_ids=[str(k.id) for k in user_keys])
    summary = await analytics.get_usage_summary(AnalyticsTimeframe.DAY, filters)
    
    # Get endpoint analytics
    endpoint_data = await analytics.get_endpoint_analytics(
        AnalyticsTimeframe.DAY, filters, limit=1
    )
    
    top_endpoint = endpoint_data[0]["endpoint"] if endpoint_data else None
    
    # Get last activity
    last_activity = None
    if user_keys:
        last_used_times = [k.last_used_at for k in user_keys if k.last_used_at]
        if last_used_times:
            last_activity = max(last_used_times).isoformat()
    
    return DashboardStats(
        total_api_keys=total_keys,
        active_keys=active_keys,
        expiring_soon=expiring_soon,
        total_requests_today=summary["summary"]["total_requests"],
        error_rate_today=summary["summary"]["error_rate_percent"],
        avg_response_time=summary["summary"]["average_response_time_ms"],
        top_endpoint=top_endpoint,
        last_activity=last_activity
    )


@router.get("/frontend/dashboard", response_model=DashboardStats, tags=["UI - Frontend"])
async def get_frontend_dashboard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """
    Get dashboard statistics for the frontend (JWT authenticated).
    """
    from sqlalchemy import select, and_
    
    # Get user's API keys
    keys_query = select(APIKey).where(
        and_(APIKey.user_id == user.id, APIKey.status == "active")
    )
    keys_result = await db.execute(keys_query)
    user_keys = keys_result.scalars().all()
    
    # Calculate basic stats
    total_keys = len(user_keys)
    active_keys = len([k for k in user_keys if k.status == APIKeyStatus.active])
    
    # Check for expiring keys
    now = datetime.utcnow()
    expiring_soon = len([
        k for k in user_keys 
        if k.expires_at and (k.expires_at - now).days <= 30
    ])
    
    # Get usage analytics
    analytics = APIUsageAnalytics(db)
    
    # User-specific analytics
    filters = AnalyticsFilter(api_key_ids=[str(k.id) for k in user_keys])
    
    summary = await analytics.get_usage_summary(AnalyticsTimeframe.DAY, filters)
    
    # Get endpoint analytics
    endpoint_data = await analytics.get_endpoint_analytics(
        AnalyticsTimeframe.DAY, filters, limit=1
    )
    
    top_endpoint = endpoint_data[0]["endpoint"] if endpoint_data else None
    
    # Get last activity
    last_activity = None
    if user_keys:
        last_used_times = [k.last_used_at for k in user_keys if k.last_used_at]
        if last_used_times:
            last_activity = max(last_used_times).isoformat()
    
    return DashboardStats(
        total_api_keys=total_keys,
        active_keys=active_keys,
        expiring_soon=expiring_soon,
        total_requests_today=summary["summary"]["total_requests"],
        error_rate_today=summary["summary"]["error_rate_percent"],
        avg_response_time=summary["summary"]["average_response_time_ms"],
        top_endpoint=top_endpoint,
        last_activity=last_activity
    )


@router.get("/api-keys", response_model=List[APIKeyCard], tags=["UI - Frontend"])
async def get_api_keys_for_ui(
    status_filter: Optional[str] = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|last_used_at|name|expires_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get API keys formatted for UI display.
    
    Returns enriched API key data with lifecycle status, usage metrics,
    and recommendations for building rich UI components.
    """
    checker = PermissionChecker(api_key)
    
    # Build query
    if checker.can(ResourceType.API_KEY, Permission.MANAGE):
        # Admin can see all keys
        query = select(APIKey)
    else:
        # Regular user sees only their keys
        query = select(APIKey).where(APIKey.user_id == api_key.user_id)
    
    # Apply filters
    if status_filter:
        try:
            status_enum = APIKeyStatus(status_filter)
            query = query.where(APIKey.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (APIKey.name.ilike(search_term)) |
            (APIKey.description.ilike(search_term)) |
            (APIKey.key_id.ilike(search_term))
        )
    
    # Apply sorting
    if sort_by == "created_at":
        order_col = APIKey.created_at
    elif sort_by == "last_used_at":
        order_col = APIKey.last_used_at
    elif sort_by == "name":
        order_col = APIKey.name
    elif sort_by == "expires_at":
        order_col = APIKey.expires_at
    else:
        order_col = APIKey.created_at
    
    if sort_order == "desc":
        query = query.order_by(desc(order_col))
    else:
        query = query.order_by(order_col)
    
    result = await db.execute(query)
    keys = result.scalars().all()
    
    # Enrich with additional data
    lifecycle_manager = APIKeyLifecycleManager()
    usage_tracker = get_usage_tracker()
    cards = []
    
    for key in keys:
        # Get lifecycle status
        lifecycle_status = await lifecycle_manager.get_lifecycle_status(str(key.id))
        
        # Get today's usage
        usage_metrics = await usage_tracker.get_api_key_metrics(str(key.id), hours=24)
        usage_today = usage_metrics.get("metrics", {}).get("total_requests", 0)
        error_rate = usage_metrics.get("metrics", {}).get("error_rate", 0)
        
        # Calculate days until expiry
        days_until_expiry = None
        if key.expires_at:
            days_until_expiry = (key.expires_at - datetime.utcnow()).days
        
        # Get recommendations
        recommendations = []
        if "error" not in lifecycle_status:
            recommendations = lifecycle_status.get("recommendations", [])
        
        card = APIKeyCard(
            id=str(key.id),
            key_id=key.key_id,
            name=key.name,
            status=key.status.value,
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
            expires_at=key.expires_at.isoformat() if key.expires_at else None,
            days_until_expiry=days_until_expiry,
            scopes=key.scopes or [],
            lifecycle_status=lifecycle_status.get("lifecycle_status", "unknown") if "error" not in lifecycle_status else "unknown",
            usage_today=usage_today,
            error_rate=error_rate,
            recommendations=recommendations[:3]  # Limit to top 3 recommendations
        )
        cards.append(card)
    
    return cards


@router.get("/quick-actions", response_model=QuickActions, tags=["UI - Legacy"], deprecated=True)
async def get_quick_actions(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get available quick actions for the current user.
    
    Returns what actions the user can perform based on their permissions.
    """
    checker = PermissionChecker(api_key)
    
    can_create = checker.can(ResourceType.API_KEY, Permission.CREATE)
    can_rotate = checker.can(ResourceType.API_KEY, Permission.UPDATE)
    can_delete = checker.can(ResourceType.API_KEY, Permission.DELETE)
    can_view_analytics = checker.can(ResourceType.ANALYTICS, Permission.READ)
    can_manage_all = checker.can(ResourceType.API_KEY, Permission.MANAGE)
    
    # Generate contextual suggestions
    suggestions = []
    
    if not can_view_analytics:
        suggestions.append("Request analytics permissions to view usage data")
    
    if can_create and not api_key.expires_at:
        suggestions.append("Set an expiration date for your API keys")
    
    if can_rotate:
        suggestions.append("Enable auto-rotation for better security")
    
    if can_view_analytics:
        suggestions.append("Review your API usage patterns")
    
    return QuickActions(
        can_create=can_create,
        can_rotate=can_rotate,
        can_delete=can_delete,
        can_view_analytics=can_view_analytics,
        can_manage_all=can_manage_all,
        suggestions=suggestions
    )


@router.get("/system-health", response_model=SystemHealth)
async def get_system_health(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ))
):
    """
    Get system health status for UI monitoring.
    
    Returns overall system health indicators and recent alerts.
    """
    usage_tracker = get_usage_tracker()
    metrics = usage_tracker.get_realtime_metrics()
    
    realtime_stats = metrics.get("realtime_stats", {})
    cached_metrics = metrics.get("cached_metrics", {})
    
    # Determine overall health status
    error_rate = realtime_stats.get("error_rate", 0)
    avg_response_time = realtime_stats.get("avg_response_time", 0)
    
    if error_rate > 10 or avg_response_time > 2000:
        health_status = "critical"
    elif error_rate > 5 or avg_response_time > 1000:
        health_status = "warning"
    else:
        health_status = "healthy"
    
    # Generate recent alerts
    recent_alerts = []
    if error_rate > 5:
        recent_alerts.append(f"High error rate: {error_rate:.1f}%")
    if avg_response_time > 1000:
        recent_alerts.append(f"Slow response times: {avg_response_time:.0f}ms")
    
    # Mock uptime calculation (in production, this would be tracked)
    uptime_hours = 24.5  # Placeholder
    
    return SystemHealth(
        status=health_status,
        uptime_hours=uptime_hours,
        total_requests=realtime_stats.get("total_requests", 0),
        error_rate=error_rate,
        response_time=avg_response_time,
        active_keys=realtime_stats.get("active_api_keys", 0),
        recent_alerts=recent_alerts
    )


@router.get("/notifications", response_model=List[UINotification])
async def get_ui_notifications(
    limit: int = Query(10, ge=1, le=50),
    api_key: APIKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_database)
):
    """
    Get UI notifications for the current user.
    
    Returns actionable notifications about API keys, usage, and system status.
    """
    notifications = []
    checker = PermissionChecker(api_key)
    
    # Check for expiring keys
    lifecycle_manager = APIKeyLifecycleManager()
    expiring_notifications = await lifecycle_manager.check_expiring_keys(30)
    
    # Filter to user's keys if not admin
    if not checker.can(ResourceType.ADMIN, Permission.READ):
        user_key_ids = [str(api_key.user_id)]
        expiring_notifications = [
            n for n in expiring_notifications 
            if n.user_id in user_key_ids
        ]
    
    # Convert to UI notifications
    for notification in expiring_notifications[:5]:  # Limit to 5 expiring keys
        if notification.notification_type == "expired":
            notif_type = "error"
            title = "API Key Expired"
        elif notification.notification_type == "critical":
            notif_type = "error"
            title = "API Key Expiring Soon"
        elif notification.notification_type == "urgent":
            notif_type = "warning"
            title = "API Key Expiring"
        else:
            notif_type = "info"
            title = "API Key Expiration Notice"
        
        ui_notification = UINotification(
            id=f"expiry_{notification.api_key_id}",
            type=notif_type,
            title=title,
            message=f"Key '{notification.key_name}' expires in {notification.days_until_expiry} days",
            action_url=f"/lifecycle/rotate/{notification.api_key_id}",
            action_text="Rotate Key",
            created_at=datetime.utcnow().isoformat(),
            read=False
        )
        notifications.append(ui_notification)
    
    # Check for high error rates
    usage_tracker = get_usage_tracker()
    user_metrics = await usage_tracker.get_api_key_metrics(str(api_key.id), hours=24)
    error_rate = user_metrics.get("metrics", {}).get("error_rate", 0)
    
    if error_rate > 10:
        error_notification = UINotification(
            id=f"error_rate_{api_key.id}",
            type="warning",
            title="High Error Rate Detected",
            message=f"Your API key has a {error_rate:.1f}% error rate in the last 24 hours",
            action_url="/analytics/my-key",
            action_text="View Analytics",
            created_at=datetime.utcnow().isoformat(),
            read=False
        )
        notifications.append(error_notification)
    
    # Add security recommendations
    if not api_key.allowed_ips:
        security_notification = UINotification(
            id=f"security_{api_key.id}",
            type="info",
            title="Security Recommendation",
            message="Consider restricting your API key to specific IP addresses",
            action_url=f"/api-keys/{api_key.id}",
            action_text="Update Settings",
            created_at=datetime.utcnow().isoformat(),
            read=False
        )
        notifications.append(security_notification)
    
    return notifications[:limit]


@router.get("/charts/usage-trend")
async def get_usage_trend_chart(
    days: int = Query(7, ge=1, le=30),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get usage trend data for charts.
    
    Returns time series data formatted for frontend charting libraries.
    """
    analytics = APIUsageAnalytics(db)
    checker = PermissionChecker(api_key)
    
    # Set up filters based on permissions
    if checker.can(ResourceType.ADMIN, Permission.READ):
        filters = None  # Admin sees all data
    else:
        # User sees only their keys
        user_keys_query = select(APIKey).where(APIKey.user_id == api_key.user_id)
        keys_result = await db.execute(user_keys_query)
        user_keys = keys_result.scalars().all()
        filters = AnalyticsFilter(api_key_ids=[str(k.id) for k in user_keys])
    
    # Get time series data
    timeframe = AnalyticsTimeframe.CUSTOM
    if not filters:
        filters = AnalyticsFilter()
    
    filters.start_date = datetime.utcnow() - timedelta(days=days)
    filters.end_date = datetime.utcnow()
    
    from ..core.analytics import MetricType
    
    # Get multiple metrics for the chart
    requests_data = await analytics.get_time_series_data(
        MetricType.REQUESTS, timeframe, "day", filters
    )
    
    error_rate_data = await analytics.get_time_series_data(
        MetricType.ERROR_RATE, timeframe, "day", filters
    )
    
    response_time_data = await analytics.get_time_series_data(
        MetricType.RESPONSE_TIME, timeframe, "day", filters
    )
    
    # Format for charts
    chart_data = {
        "labels": [point["timestamp"][:10] for point in requests_data],  # YYYY-MM-DD
        "datasets": [
            {
                "label": "Requests",
                "data": [point["value"] for point in requests_data],
                "type": "line",
                "yAxisID": "requests"
            },
            {
                "label": "Error Rate (%)",
                "data": [point["value"] for point in error_rate_data],
                "type": "line",
                "yAxisID": "percentage"
            },
            {
                "label": "Response Time (ms)",
                "data": [point["value"] for point in response_time_data],
                "type": "line",
                "yAxisID": "time"
            }
        ]
    }
    
    return chart_data


@router.get("/charts/endpoint-performance")
async def get_endpoint_performance_chart(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get endpoint performance data for charts.
    
    Returns endpoint analytics formatted for performance charts.
    """
    analytics = APIUsageAnalytics(db)
    checker = PermissionChecker(api_key)
    
    # Set up filters
    if checker.can(ResourceType.ADMIN, Permission.READ):
        filters = None
    else:
        user_keys_query = select(APIKey).where(APIKey.user_id == api_key.user_id)
        keys_result = await db.execute(user_keys_query)
        user_keys = keys_result.scalars().all()
        filters = AnalyticsFilter(api_key_ids=[str(k.id) for k in user_keys])
    
    # Get endpoint data
    endpoint_data = await analytics.get_endpoint_analytics(
        AnalyticsTimeframe.DAY, filters, limit=10
    )
    
    # Format for charts
    chart_data = {
        "labels": [ep["endpoint"] for ep in endpoint_data],
        "datasets": [
            {
                "label": "Total Requests",
                "data": [ep["total_requests"] for ep in endpoint_data],
                "backgroundColor": "rgba(54, 162, 235, 0.6)"
            },
            {
                "label": "Error Rate (%)",
                "data": [ep["error_rate_percent"] for ep in endpoint_data],
                "backgroundColor": "rgba(255, 99, 132, 0.6)"
            },
            {
                "label": "Avg Response Time (ms)",
                "data": [ep["average_response_time_ms"] for ep in endpoint_data],
                "backgroundColor": "rgba(75, 192, 192, 0.6)"
            }
        ]
    }
    
    return chart_data


# Admin UI endpoints
@router.get("/admin/overview")
async def get_admin_overview(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get admin overview data for admin dashboard.
    
    Returns system-wide statistics and health indicators.
    """
    # Get system-wide statistics
    total_keys_query = select(func.count(APIKey.id))
    total_keys_result = await db.execute(total_keys_query)
    total_keys = total_keys_result.scalar()
    
    active_keys_query = select(func.count(APIKey.id)).where(APIKey.status == APIKeyStatus.active)
    active_keys_result = await db.execute(active_keys_query)
    active_keys = active_keys_result.scalar()
    
    # Get users count
    total_users_query = select(func.count(User.id))
    total_users_result = await db.execute(total_users_query)
    total_users = total_users_result.scalar()
    
    # Get usage metrics
    usage_tracker = get_usage_tracker()
    system_metrics = usage_tracker.get_realtime_metrics()
    
    # Get recent activity
    recent_keys_query = select(APIKey).order_by(desc(APIKey.created_at)).limit(5)
    recent_keys_result = await db.execute(recent_keys_query)
    recent_keys = recent_keys_result.scalars().all()
    
    return {
        "system_stats": {
            "total_api_keys": total_keys,
            "active_api_keys": active_keys,
            "total_users": total_users,
            "system_health": system_metrics
        },
        "recent_activity": [
            {
                "key_id": key.key_id,
                "name": key.name,
                "created_at": key.created_at.isoformat(),
                "status": key.status.value
            }
            for key in recent_keys
        ]
    }


@router.get("/config")
async def get_ui_config(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get UI configuration and feature flags.
    
    Returns configuration needed for frontend applications.
    """
    checker = PermissionChecker(api_key)
    
    return {
        "features": {
            "analytics": checker.can(ResourceType.ANALYTICS, Permission.READ),
            "admin_panel": checker.can(ResourceType.ADMIN, Permission.READ),
            "key_management": checker.can(ResourceType.API_KEY, Permission.UPDATE),
            "export_data": checker.can(ResourceType.ANALYTICS, Permission.EXPORT),
            "lifecycle_management": True,
            "rate_limiting": True,
            "auto_rotation": True
        },
        "limits": {
            "max_api_keys": 50,  # Could be configurable per user
            "max_scopes": len(list(APIKeyScope)),
            "max_name_length": 100,
            "max_description_length": 500
        },
        "defaults": {
            "expiration_days": 90,
            "rate_limit": 1000,
            "rate_limit_period": "requests_per_hour",
            "auto_rotation_days": 90
        },
        "theme": {
            "primary_color": "#3B82F6",
            "success_color": "#10B981",
            "warning_color": "#F59E0B",
            "error_color": "#EF4444"
        }
    }