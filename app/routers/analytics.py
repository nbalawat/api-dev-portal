"""
Analytics Router

API endpoints for accessing usage analytics, generating reports,
and monitoring API key performance and system health metrics.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.analytics import (
    APIUsageAnalytics, AnalyticsTimeframe, MetricType, 
    AnalyticsFilter, UsageMetric, AnalyticsReport
)
from ..middleware.permissions import require_resource_permission, get_permission_checker, PermissionChecker
from ..middleware import require_api_key
from ..core.permissions import ResourceType, Permission
from ..models.api_key import APIKey
from ..dependencies.database import get_database


router = APIRouter(prefix="/analytics", tags=["Analytics & Reporting"])


# Request/Response Models
class AnalyticsFilterRequest(BaseModel):
    """Request model for analytics filters."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    api_key_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    endpoints: Optional[List[str]] = None
    methods: Optional[List[str]] = None
    status_codes: Optional[List[int]] = None
    ip_addresses: Optional[List[str]] = None
    min_response_time: Optional[float] = None
    max_response_time: Optional[float] = None


class TimeSeriesRequest(BaseModel):
    """Request model for time series data."""
    metric: MetricType
    timeframe: AnalyticsTimeframe
    interval: str = "hour"
    filters: Optional[AnalyticsFilterRequest] = None


class UsageSummaryResponse(BaseModel):
    """Response model for usage summary."""
    timeframe: str
    period: Dict[str, str]
    summary: Dict[str, float]
    bandwidth: Dict[str, float]


class EndpointAnalyticsResponse(BaseModel):
    """Response model for endpoint analytics."""
    endpoint: str
    total_requests: int
    error_count: int
    error_rate_percent: float
    average_response_time_ms: float
    unique_api_keys: int
    unique_ips: int
    methods: List[str]
    total_bandwidth_bytes: int


class InsightsResponse(BaseModel):
    """Response model for analytics insights."""
    insights: List[str]
    generated_at: datetime
    timeframe: str
    total_insights: int


# Public endpoints (require analytics permissions)
@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.DAY),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get usage summary for the current API key.
    
    Returns high-level metrics including request counts, error rates,
    response times, and bandwidth usage.
    """
    analytics = APIUsageAnalytics(db)
    
    # Create filter to limit to current API key
    filters = AnalyticsFilter(
        start_date=start_date,
        end_date=end_date,
        api_key_ids=[str(api_key.id)]
    )
    
    summary = await analytics.get_usage_summary(timeframe, filters)
    
    return UsageSummaryResponse(**summary)


@router.post("/time-series")
async def get_time_series_data(
    request: TimeSeriesRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get time series data for specific metrics.
    
    Useful for creating charts and graphs showing usage trends over time.
    """
    analytics = APIUsageAnalytics(db)
    
    # Convert request filters
    filters = None
    if request.filters:
        filters = AnalyticsFilter(**request.filters.dict())
    
    # Limit to current API key if not admin
    from ..middleware.permissions import PermissionChecker
    checker = PermissionChecker(api_key)
    if not checker.can(ResourceType.ADMIN, Permission.READ):
        if filters:
            filters.api_key_ids = [str(api_key.id)]
        else:
            filters = AnalyticsFilter(api_key_ids=[str(api_key.id)])
    
    time_series = await analytics.get_time_series_data(
        request.metric,
        request.timeframe,
        request.interval,
        filters
    )
    
    return {
        "metric": request.metric.value,
        "timeframe": request.timeframe.value,
        "interval": request.interval,
        "data": time_series
    }


@router.get("/my-key")
async def get_my_api_key_analytics(
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.WEEK),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get detailed analytics for the current API key.
    
    Returns comprehensive usage statistics, trends, and top endpoints.
    """
    analytics = APIUsageAnalytics(db)
    
    filters = AnalyticsFilter(
        start_date=start_date,
        end_date=end_date
    )
    
    api_key_analytics = await analytics.get_api_key_analytics(
        str(api_key.id),
        timeframe,
        filters
    )
    
    return api_key_analytics


@router.get("/endpoints", response_model=List[EndpointAnalyticsResponse])
async def get_endpoint_analytics(
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.DAY),
    limit: int = Query(20, ge=1, le=100),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get analytics for individual endpoints.
    
    Shows performance and usage metrics for each API endpoint.
    """
    analytics = APIUsageAnalytics(db)
    
    # Limit to current API key if not admin
    from ..middleware.permissions import PermissionChecker
    checker = PermissionChecker(api_key)
    filters = AnalyticsFilter(start_date=start_date, end_date=end_date)
    
    if not checker.can(ResourceType.ADMIN, Permission.READ):
        filters.api_key_ids = [str(api_key.id)]
    
    endpoint_data = await analytics.get_endpoint_analytics(
        timeframe, filters, limit
    )
    
    return [EndpointAnalyticsResponse(**ep) for ep in endpoint_data]


@router.get("/insights", response_model=InsightsResponse)
async def get_analytics_insights(
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.DAY),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get AI-generated insights from usage data.
    
    Returns actionable recommendations based on usage patterns,
    performance metrics, and error rates.
    """
    analytics = APIUsageAnalytics(db)
    
    # Limit to current API key if not admin
    from ..middleware.permissions import PermissionChecker
    checker = PermissionChecker(api_key)
    filters = AnalyticsFilter(start_date=start_date, end_date=end_date)
    
    if not checker.can(ResourceType.ADMIN, Permission.READ):
        filters.api_key_ids = [str(api_key.id)]
    
    insights = await analytics.generate_insights(timeframe, filters)
    
    return InsightsResponse(
        insights=insights,
        generated_at=datetime.utcnow(),
        timeframe=timeframe.value,
        total_insights=len(insights)
    )


# Admin endpoints (require admin analytics permissions)
@router.get("/admin/overview")
async def get_admin_analytics_overview(
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.DAY),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get system-wide analytics overview (admin only).
    
    Returns comprehensive metrics across all API keys and users.
    """
    analytics = APIUsageAnalytics(db)
    
    # Get overall summary (no API key filter)
    summary = await analytics.get_usage_summary(timeframe)
    
    # Get top performing API keys
    endpoint_data = await analytics.get_endpoint_analytics(timeframe, limit=10)
    
    # Generate system insights
    insights = await analytics.generate_insights(timeframe)
    
    return {
        "overview": summary,
        "top_endpoints": endpoint_data[:5],
        "system_insights": insights,
        "admin_metrics": {
            "timeframe": timeframe.value,
            "generated_at": datetime.utcnow().isoformat()
        }
    }


@router.get("/admin/api-key/{api_key_id}")
async def get_admin_api_key_analytics(
    api_key_id: str,
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.WEEK),
    admin_api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get analytics for any API key (admin only).
    
    Allows administrators to view detailed analytics for any API key in the system.
    """
    analytics = APIUsageAnalytics(db)
    
    api_key_analytics = await analytics.get_api_key_analytics(
        api_key_id, timeframe
    )
    
    if "error" in api_key_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_key_analytics["error"]
        )
    
    return api_key_analytics


@router.get("/admin/user/{user_id}")
async def get_admin_user_analytics(
    user_id: str,
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.WEEK),
    admin_api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get analytics for all API keys belonging to a user (admin only).
    
    Provides user-level analytics across all their API keys.
    """
    analytics = APIUsageAnalytics(db)
    
    user_analytics = await analytics.get_user_analytics(
        user_id, timeframe
    )
    
    if "error" in user_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=user_analytics["error"]
        )
    
    return user_analytics


@router.post("/admin/custom-report")
async def generate_custom_report(
    report_request: Dict[str, Any],
    admin_api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Generate a custom analytics report (admin only).
    
    Allows administrators to create detailed reports with custom filters,
    metrics, and time ranges.
    """
    analytics = APIUsageAnalytics(db)
    
    # Extract parameters from request
    timeframe = AnalyticsTimeframe(report_request.get("timeframe", "day"))
    
    # Build filters from request
    filters = None
    if "filters" in report_request:
        filter_data = report_request["filters"]
        filters = AnalyticsFilter(**filter_data)
    
    # Generate comprehensive report
    summary = await analytics.get_usage_summary(timeframe, filters)
    endpoint_data = await analytics.get_endpoint_analytics(timeframe, filters)
    insights = await analytics.generate_insights(timeframe, filters)
    
    # Get time series data for multiple metrics
    time_series_data = {}
    metrics = report_request.get("metrics", ["requests", "response_time", "error_rate"])
    
    for metric_name in metrics:
        try:
            metric = MetricType(metric_name)
            time_series = await analytics.get_time_series_data(
                metric, timeframe, "hour", filters
            )
            time_series_data[metric_name] = time_series
        except ValueError:
            continue  # Skip invalid metrics
    
    return {
        "report": {
            "title": f"Custom Analytics Report - {timeframe.value.title()}",
            "generated_at": datetime.utcnow().isoformat(),
            "timeframe": timeframe.value,
            "summary": summary,
            "endpoint_analytics": endpoint_data,
            "time_series": time_series_data,
            "insights": insights
        },
        "metadata": {
            "total_endpoints": len(endpoint_data),
            "total_insights": len(insights),
            "metrics_included": list(time_series_data.keys()),
            "filters_applied": bool(filters)
        }
    }


# Export endpoints (require export permissions)
@router.get("/export/csv")
async def export_analytics_csv(
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.DAY),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.EXPORT)),
    db: AsyncSession = Depends(get_database)
):
    """
    Export analytics data as CSV.
    
    Returns usage data in CSV format for external analysis tools.
    """
    # This would implement actual CSV generation
    # For now, return metadata about what would be exported
    
    return {
        "message": "CSV export functionality",
        "note": "This endpoint would generate and return actual CSV data",
        "format": "text/csv",
        "timeframe": timeframe.value,
        "api_key_id": api_key.key_id,
        "estimated_rows": "Would query database for actual count",
        "columns": [
            "timestamp", "endpoint", "method", "status_code",
            "response_time_ms", "ip_address", "user_agent",
            "request_size_bytes", "response_size_bytes"
        ]
    }


@router.get("/export/json")
async def export_analytics_json(
    timeframe: AnalyticsTimeframe = Query(AnalyticsTimeframe.DAY),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.EXPORT)),
    db: AsyncSession = Depends(get_database)
):
    """
    Export analytics data as JSON.
    
    Returns comprehensive analytics data in structured JSON format.
    """
    analytics = APIUsageAnalytics(db)
    
    # Create filter for current API key
    checker = PermissionChecker(api_key)
    filters = AnalyticsFilter(start_date=start_date, end_date=end_date)
    
    if not checker.can(ResourceType.ADMIN, Permission.READ):
        filters.api_key_ids = [str(api_key.id)]
    
    # Get comprehensive data
    summary = await analytics.get_usage_summary(timeframe, filters)
    endpoint_data = await analytics.get_endpoint_analytics(timeframe, filters)
    insights = await analytics.generate_insights(timeframe, filters)
    
    return {
        "export_metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "timeframe": timeframe.value,
            "api_key_id": api_key.key_id,
            "format": "json"
        },
        "data": {
            "summary": summary,
            "endpoints": endpoint_data,
            "insights": insights
        }
    }


# Utility endpoints
@router.get("/available-metrics")
async def get_available_metrics(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.READ))
):
    """
    Get list of available metrics for analytics.
    
    Returns all metrics that can be used in time series and reports.
    """
    return {
        "metrics": [
            {
                "name": metric.value,
                "description": {
                    "requests": "Total number of API requests",
                    "response_time": "Average response time in milliseconds", 
                    "error_rate": "Percentage of requests that resulted in errors",
                    "bandwidth": "Total bandwidth usage in bytes",
                    "unique_ips": "Number of unique IP addresses",
                    "endpoint_popularity": "Relative popularity of endpoints",
                    "success_rate": "Percentage of successful requests"
                }.get(metric.value, "Metric description")
            }
            for metric in MetricType
        ],
        "timeframes": [
            {
                "name": timeframe.value,
                "description": {
                    "hour": "Last 60 minutes",
                    "day": "Last 24 hours",
                    "week": "Last 7 days", 
                    "month": "Last 30 days",
                    "quarter": "Last 90 days",
                    "year": "Last 365 days",
                    "custom": "Custom date range"
                }.get(timeframe.value, "Timeframe description")
            }
            for timeframe in AnalyticsTimeframe
        ]
    }