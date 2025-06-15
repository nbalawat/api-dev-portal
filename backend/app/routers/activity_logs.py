"""
Activity Logs Router

Endpoints for accessing and analyzing API key activity logs.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.permissions import require_resource_permission, get_permission_checker, PermissionChecker
from ..middleware import require_api_key
from ..core.permissions import ResourceType, Permission
from ..models.api_key import APIKey
from ..dependencies.database import get_database
from ..services.activity_logging import (
    get_activity_logger, ActivityType, Severity, ActivityLogger
)


router = APIRouter(prefix="/activity-logs", tags=["Activity Logs"])


# Response Models
class ActivityLogResponse(BaseModel):
    """Activity log entry response model."""
    id: str
    timestamp: str
    activity_type: str
    severity: str
    api_key_id: Optional[str]
    user_id: Optional[str]
    source_ip: Optional[str]
    user_agent: Optional[str]
    endpoint: Optional[str]
    method: Optional[str]
    status_code: Optional[int]
    response_time_ms: Optional[float]
    details: Dict[str, Any]
    tags: List[str]
    session_id: Optional[str]
    request_id: Optional[str]


class ActivitySummaryResponse(BaseModel):
    """Activity summary response model."""
    time_period: Dict[str, Any]
    summary: Dict[str, Any]
    recent_activities: List[Dict[str, Any]]
    security_events: List[Dict[str, Any]]


class AnomalyDetectionResponse(BaseModel):
    """Anomaly detection response model."""
    api_key_id: str
    analysis_period_hours: int
    anomalies_detected: int
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]


# Activity Log Endpoints
@router.get("/my-activities", response_model=List[ActivityLogResponse])
async def get_my_activities(
    activity_types: Optional[str] = Query(None, description="Comma-separated activity types"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (1-168)"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    api_key: APIKey = Depends(require_api_key),
    logger: ActivityLogger = Depends(get_activity_logger)
):
    """
    Get activity logs for the current API key.
    
    Returns activities related to the current API key with optional filtering.
    """
    # Parse activity types
    activity_type_filter = None
    if activity_types:
        try:
            activity_type_filter = [
                ActivityType(t.strip()) for t in activity_types.split(',')
            ]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid activity type: {e}"
            )
    
    # Parse severity
    severity_filter = None
    if severity:
        try:
            severity_filter = Severity(severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}"
            )
    
    # Calculate time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)
    
    # Get activities
    activities = await logger.get_activity_logs(
        api_key_id=str(api_key.id),
        activity_types=activity_type_filter,
        severity_filter=severity_filter,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    # Convert to response format
    response_activities = []
    for activity in activities:
        response_activities.append(ActivityLogResponse(
            id=activity['id'],
            timestamp=activity['timestamp'].isoformat(),
            activity_type=activity['activity_type'],
            severity=activity['severity'],
            api_key_id=activity['api_key_id'],
            user_id=activity['user_id'],
            source_ip=activity['source_ip'],
            user_agent=activity['user_agent'],
            endpoint=activity['endpoint'],
            method=activity['method'],
            status_code=activity['status_code'],
            response_time_ms=activity['response_time_ms'],
            details=activity['details'],
            tags=activity['tags'],
            session_id=activity['session_id'],
            request_id=activity['request_id']
        ))
    
    return response_activities


@router.get("/my-summary", response_model=ActivitySummaryResponse)
async def get_my_activity_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze (1-168)"),
    api_key: APIKey = Depends(require_api_key),
    logger: ActivityLogger = Depends(get_activity_logger)
):
    """
    Get activity summary for the current API key.
    
    Returns aggregated statistics and insights about API key usage.
    """
    summary = await logger.get_activity_summary(
        api_key_id=str(api_key.id),
        hours=hours
    )
    
    return ActivitySummaryResponse(**summary)


@router.get("/my-anomalies", response_model=AnomalyDetectionResponse)
async def detect_my_anomalies(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze for anomalies"),
    api_key: APIKey = Depends(require_api_key),
    logger: ActivityLogger = Depends(get_activity_logger)
):
    """
    Detect anomalous activities for the current API key.
    
    Analyzes activity patterns to identify potential security concerns.
    """
    anomalies = await logger.detect_anomalies(
        api_key_id=str(api_key.id),
        hours=hours
    )
    
    # Generate recommendations based on anomalies
    recommendations = []
    for anomaly in anomalies:
        if anomaly['type'] == 'repeated_auth_failures':
            recommendations.append("Consider rotating your API key if you see unexpected auth failures")
            recommendations.append("Verify that your applications are using the correct API key")
        elif anomaly['type'] == 'multiple_source_ips':
            recommendations.append("Consider restricting your API key to specific IP addresses")
            recommendations.append("Review if all IP addresses are expected for your use case")
        elif anomaly['type'] == 'frequent_rate_limiting':
            recommendations.append("Consider increasing your rate limits or optimizing request patterns")
            recommendations.append("Implement exponential backoff in your applications")
    
    # Remove duplicates
    recommendations = list(set(recommendations))
    
    return AnomalyDetectionResponse(
        api_key_id=str(api_key.id),
        analysis_period_hours=hours,
        anomalies_detected=len(anomalies),
        anomalies=anomalies,
        recommendations=recommendations
    )


# Admin endpoints for viewing all activities
@router.get("/admin/all-activities", response_model=List[ActivityLogResponse])
async def get_all_activities(
    api_key_id: Optional[str] = Query(None, description="Filter by API key ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    activity_types: Optional[str] = Query(None, description="Comma-separated activity types"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    logger: ActivityLogger = Depends(get_activity_logger)
):
    """
    Get all activity logs (admin only).
    
    Provides system-wide access to activity logs for administrative purposes.
    """
    # Parse filters
    activity_type_filter = None
    if activity_types:
        try:
            activity_type_filter = [
                ActivityType(t.strip()) for t in activity_types.split(',')
            ]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid activity type: {e}"
            )
    
    severity_filter = None
    if severity:
        try:
            severity_filter = Severity(severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}"
            )
    
    # Calculate time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)
    
    # Get activities
    activities = await logger.get_activity_logs(
        api_key_id=api_key_id,
        user_id=user_id,
        activity_types=activity_type_filter,
        severity_filter=severity_filter,
        start_date=start_date,
        end_date=end_date,
        source_ip=source_ip,
        limit=limit,
        offset=offset
    )
    
    # Convert to response format
    response_activities = []
    for activity in activities:
        response_activities.append(ActivityLogResponse(
            id=activity['id'],
            timestamp=activity['timestamp'].isoformat(),
            activity_type=activity['activity_type'],
            severity=activity['severity'],
            api_key_id=activity['api_key_id'],
            user_id=activity['user_id'],
            source_ip=activity['source_ip'],
            user_agent=activity['user_agent'],
            endpoint=activity['endpoint'],
            method=activity['method'],
            status_code=activity['status_code'],
            response_time_ms=activity['response_time_ms'],
            details=activity['details'],
            tags=activity['tags'],
            session_id=activity['session_id'],
            request_id=activity['request_id']
        ))
    
    return response_activities


@router.get("/admin/security-dashboard")
async def get_security_dashboard(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    logger: ActivityLogger = Depends(get_activity_logger)
):
    """
    Get security dashboard data (admin only).
    
    Returns security-focused metrics and alerts for administrative monitoring.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)
    
    # Get security-related activities
    security_activities = await logger.get_activity_logs(
        activity_types=[
            ActivityType.AUTH_FAILED,
            ActivityType.AUTH_BLOCKED,
            ActivityType.RATE_LIMIT_EXCEEDED,
            ActivityType.SUSPICIOUS_ACTIVITY,
            ActivityType.IP_BLOCKED,
            ActivityType.BRUTE_FORCE_DETECTED
        ],
        start_date=start_date,
        end_date=end_date,
        limit=1000
    )
    
    # Get all activities for broader analysis
    all_activities = await logger.get_activity_logs(
        start_date=start_date,
        end_date=end_date,
        limit=5000
    )
    
    # Security metrics
    failed_auth_count = len([
        a for a in security_activities 
        if a['activity_type'] == ActivityType.AUTH_FAILED.value
    ])
    
    rate_limit_violations = len([
        a for a in security_activities 
        if a['activity_type'] == ActivityType.RATE_LIMIT_EXCEEDED.value
    ])
    
    suspicious_activities = len([
        a for a in security_activities 
        if a['activity_type'] == ActivityType.SUSPICIOUS_ACTIVITY.value
    ])
    
    # Top source IPs by failed authentications
    failed_auth_ips = {}
    for activity in security_activities:
        if activity['activity_type'] == ActivityType.AUTH_FAILED.value and activity['source_ip']:
            ip = activity['source_ip']
            failed_auth_ips[ip] = failed_auth_ips.get(ip, 0) + 1
    
    top_failed_ips = sorted(
        failed_auth_ips.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:10]
    
    # Most targeted API keys
    targeted_keys = {}
    for activity in security_activities:
        if activity['api_key_id']:
            key_id = activity['api_key_id']
            targeted_keys[key_id] = targeted_keys.get(key_id, 0) + 1
    
    most_targeted = sorted(
        targeted_keys.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:10]
    
    # Recent critical events
    critical_events = [
        a for a in all_activities 
        if a['severity'] == Severity.CRITICAL.value
    ][-10:]  # Last 10 critical events
    
    return {
        "time_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "hours": hours
        },
        "security_metrics": {
            "failed_authentications": failed_auth_count,
            "rate_limit_violations": rate_limit_violations,
            "suspicious_activities": suspicious_activities,
            "total_security_events": len(security_activities)
        },
        "threat_analysis": {
            "top_failed_auth_ips": [
                {"ip": ip, "failed_attempts": count}
                for ip, count in top_failed_ips
            ],
            "most_targeted_api_keys": [
                {"api_key_id": key_id, "incident_count": count}
                for key_id, count in most_targeted
            ]
        },
        "recent_critical_events": critical_events,
        "recommendations": [
            "Monitor API keys with high failure rates",
            "Consider implementing IP blocking for repeated failures",
            "Review rate limiting policies for frequently violated keys",
            "Enable notifications for critical security events"
        ]
    }


@router.get("/admin/export")
async def export_activity_logs(
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
    api_key_id: Optional[str] = Query(None, description="Filter by API key ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours to export"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.EXPORT)),
    logger: ActivityLogger = Depends(get_activity_logger)
):
    """
    Export activity logs (admin only).
    
    Exports activity logs in the specified format for external analysis.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)
    
    activities = await logger.get_activity_logs(
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date,
        limit=10000  # Large limit for export
    )
    
    if format == "json":
        return {
            "export_metadata": {
                "format": "json",
                "exported_at": datetime.utcnow().isoformat(),
                "time_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_records": len(activities),
                "filters": {
                    "api_key_id": api_key_id,
                    "hours": hours
                }
            },
            "activities": activities
        }
    
    elif format == "csv":
        # In a real implementation, this would return actual CSV data
        return {
            "message": "CSV export would be generated here",
            "export_info": {
                "format": "csv",
                "total_records": len(activities),
                "note": "This would typically return CSV data with proper Content-Type headers"
            }
        }