"""
API Key Activity Logging Service

Comprehensive logging service for tracking all API key-related activities,
security events, and administrative actions.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.orm import sessionmaker

from ..core.database import get_db
from ..models.api_key import APIKey
from ..models.user import User


class ActivityType(str, Enum):
    """Types of activities that can be logged."""
    # API Key Management
    KEY_CREATED = "key_created"
    KEY_UPDATED = "key_updated"
    KEY_REVOKED = "key_revoked"
    KEY_DELETED = "key_deleted"
    KEY_ROTATED = "key_rotated"
    KEY_EXPIRED = "key_expired"
    KEY_SUSPENDED = "key_suspended"
    KEY_ACTIVATED = "key_activated"
    
    # Authentication Events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    AUTH_BLOCKED = "auth_blocked"
    
    # Permission Events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    SCOPE_CHANGED = "scope_changed"
    
    # Rate Limiting Events
    RATE_LIMIT_HIT = "rate_limit_hit"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_RESET = "rate_limit_reset"
    
    # Security Events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    IP_BLOCKED = "ip_blocked"
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    
    # Administrative Actions
    ADMIN_ACCESS = "admin_access"
    BULK_OPERATION = "bulk_operation"
    SYSTEM_MAINTENANCE = "system_maintenance"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    
    # Usage Events
    ENDPOINT_ACCESSED = "endpoint_accessed"
    HIGH_USAGE_DETECTED = "high_usage_detected"
    QUOTA_EXCEEDED = "quota_exceeded"


class Severity(str, Enum):
    """Activity severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ActivityLogEntry:
    """Activity log entry data structure."""
    id: str
    timestamp: datetime
    activity_type: ActivityType
    severity: Severity
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


class ActivityLogger:
    """
    Comprehensive activity logging service for API key operations.
    
    Provides centralized logging of all API key-related activities with
    different severity levels, filtering, and analysis capabilities.
    """
    
    def __init__(self):
        self.log_buffer: List[ActivityLogEntry] = []
        self.buffer_size = 100
        self.flush_interval = 30  # seconds
        self._flush_task: Optional[asyncio.Task] = None
        self._db_session_factory: Optional[sessionmaker] = None
    
    async def start(self):
        """Start the activity logging service."""
        self._db_session_factory = get_async_session()
        self._flush_task = asyncio.create_task(self._periodic_flush())
        print("✅ Activity logging service started")
    
    async def stop(self):
        """Stop the activity logging service."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining logs
        await self._flush_logs()
        print("✅ Activity logging service stopped")
    
    async def log_activity(
        self,
        activity_type: ActivityType,
        severity: Severity = Severity.LOW,
        api_key_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log an activity event."""
        entry = ActivityLogEntry(
            id=str(uuid4()),
            timestamp=datetime.utcnow(),
            activity_type=activity_type,
            severity=severity,
            api_key_id=api_key_id,
            user_id=user_id,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            details=details or {},
            tags=tags or [],
            session_id=session_id,
            request_id=request_id
        )
        
        self.log_buffer.append(entry)
        
        # Flush buffer if it's full or if it's a critical event
        if len(self.log_buffer) >= self.buffer_size or severity == Severity.CRITICAL:
            await self._flush_logs()
    
    async def log_key_creation(
        self,
        api_key_id: str,
        user_id: str,
        key_name: str,
        scopes: List[str],
        source_ip: Optional[str] = None,
        **kwargs
    ):
        """Log API key creation event."""
        await self.log_activity(
            activity_type=ActivityType.KEY_CREATED,
            severity=Severity.MEDIUM,
            api_key_id=api_key_id,
            user_id=user_id,
            source_ip=source_ip,
            details={
                "key_name": key_name,
                "scopes": scopes,
                "action": "create_api_key"
            },
            tags=["api_key", "creation"],
            **kwargs
        )
    
    async def log_authentication_attempt(
        self,
        api_key_id: Optional[str],
        success: bool,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        failure_reason: Optional[str] = None,
        **kwargs
    ):
        """Log authentication attempt."""
        activity_type = ActivityType.AUTH_SUCCESS if success else ActivityType.AUTH_FAILED
        severity = Severity.LOW if success else Severity.MEDIUM
        
        details = {
            "success": success,
            "endpoint": endpoint
        }
        
        if not success and failure_reason:
            details["failure_reason"] = failure_reason
            if "invalid" in failure_reason.lower() or "expired" in failure_reason.lower():
                severity = Severity.HIGH
        
        await self.log_activity(
            activity_type=activity_type,
            severity=severity,
            api_key_id=api_key_id,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            details=details,
            tags=["authentication"],
            **kwargs
        )
    
    async def log_rate_limit_event(
        self,
        api_key_id: str,
        event_type: str,  # "hit", "exceeded", "reset"
        limit: int,
        current_usage: int,
        source_ip: Optional[str] = None,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        """Log rate limiting event."""
        if event_type == "exceeded":
            activity_type = ActivityType.RATE_LIMIT_EXCEEDED
            severity = Severity.HIGH
        elif event_type == "hit":
            activity_type = ActivityType.RATE_LIMIT_HIT
            severity = Severity.MEDIUM
        else:
            activity_type = ActivityType.RATE_LIMIT_RESET
            severity = Severity.LOW
        
        await self.log_activity(
            activity_type=activity_type,
            severity=severity,
            api_key_id=api_key_id,
            source_ip=source_ip,
            endpoint=endpoint,
            details={
                "event_type": event_type,
                "limit": limit,
                "current_usage": current_usage,
                "usage_percentage": (current_usage / limit * 100) if limit > 0 else 0
            },
            tags=["rate_limiting"],
            **kwargs
        )
    
    async def log_security_event(
        self,
        event_type: str,
        severity: Severity,
        api_key_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log security-related event."""
        activity_type_map = {
            "suspicious_activity": ActivityType.SUSPICIOUS_ACTIVITY,
            "ip_blocked": ActivityType.IP_BLOCKED,
            "brute_force": ActivityType.BRUTE_FORCE_DETECTED
        }
        
        activity_type = activity_type_map.get(event_type, ActivityType.SUSPICIOUS_ACTIVITY)
        
        await self.log_activity(
            activity_type=activity_type,
            severity=severity,
            api_key_id=api_key_id,
            source_ip=source_ip,
            details=details or {"event_type": event_type},
            tags=["security"],
            **kwargs
        )
    
    async def log_admin_action(
        self,
        admin_user_id: str,
        action: str,
        target_resource: str,
        source_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log administrative action."""
        await self.log_activity(
            activity_type=ActivityType.ADMIN_ACCESS,
            severity=Severity.MEDIUM,
            user_id=admin_user_id,
            source_ip=source_ip,
            details={
                "admin_action": action,
                "target_resource": target_resource,
                **(details or {})
            },
            tags=["admin", "administration"],
            **kwargs
        )
    
    async def get_activity_logs(
        self,
        api_key_id: Optional[str] = None,
        user_id: Optional[str] = None,
        activity_types: Optional[List[ActivityType]] = None,
        severity_filter: Optional[Severity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        source_ip: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve activity logs with filtering.
        
        This is a simplified implementation that would typically
        query from a dedicated logging database or system.
        """
        # In a production system, this would query from a logging database
        # For now, we'll simulate retrieving from our buffer and some mock data
        
        filtered_logs = []
        
        # Filter logs from buffer
        for entry in self.log_buffer:
            if api_key_id and entry.api_key_id != api_key_id:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if activity_types and entry.activity_type not in activity_types:
                continue
            if severity_filter and entry.severity != severity_filter:
                continue
            if start_date and entry.timestamp < start_date:
                continue
            if end_date and entry.timestamp > end_date:
                continue
            if source_ip and entry.source_ip != source_ip:
                continue
            
            filtered_logs.append(asdict(entry))
        
        # Sort by timestamp (most recent first)
        filtered_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply pagination
        return filtered_logs[offset:offset + limit]
    
    async def get_activity_summary(
        self,
        api_key_id: Optional[str] = None,
        user_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get activity summary for the specified time period."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        logs = await self.get_activity_logs(
            api_key_id=api_key_id,
            user_id=user_id,
            start_date=start_time,
            end_date=end_time,
            limit=1000
        )
        
        # Calculate summary statistics
        total_activities = len(logs)
        activity_counts = {}
        severity_counts = {}
        hourly_counts = {}
        
        for log in logs:
            # Count by activity type
            activity_type = log['activity_type']
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
            
            # Count by severity
            severity = log['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count by hour
            hour = log['timestamp'].replace(minute=0, second=0, microsecond=0)
            hour_key = hour.isoformat()
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
        
        # Get most recent activities
        recent_activities = logs[:10]  # Last 10 activities
        
        return {
            "time_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "summary": {
                "total_activities": total_activities,
                "activity_types": activity_counts,
                "severity_distribution": severity_counts,
                "activities_per_hour": hourly_counts
            },
            "recent_activities": recent_activities,
            "security_events": [
                log for log in logs 
                if log['severity'] in ['high', 'critical'] or 'security' in log['tags']
            ][:5]
        }
    
    async def detect_anomalies(
        self,
        api_key_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Detect anomalous activities for an API key."""
        logs = await self.get_activity_logs(
            api_key_id=api_key_id,
            start_date=datetime.utcnow() - timedelta(hours=hours),
            limit=1000
        )
        
        anomalies = []
        
        # Check for repeated failed authentications
        failed_auths = [
            log for log in logs 
            if log['activity_type'] == ActivityType.AUTH_FAILED.value
        ]
        
        if len(failed_auths) > 10:  # More than 10 failed attempts
            anomalies.append({
                "type": "repeated_auth_failures",
                "severity": "high",
                "count": len(failed_auths),
                "description": f"Detected {len(failed_auths)} failed authentication attempts"
            })
        
        # Check for unusual source IPs
        source_ips = [log['source_ip'] for log in logs if log['source_ip']]
        unique_ips = set(source_ips)
        
        if len(unique_ips) > 5:  # More than 5 different IPs
            anomalies.append({
                "type": "multiple_source_ips",
                "severity": "medium",
                "count": len(unique_ips),
                "ips": list(unique_ips),
                "description": f"API key used from {len(unique_ips)} different IP addresses"
            })
        
        # Check for rate limit violations
        rate_limit_events = [
            log for log in logs 
            if log['activity_type'] == ActivityType.RATE_LIMIT_EXCEEDED.value
        ]
        
        if len(rate_limit_events) > 5:
            anomalies.append({
                "type": "frequent_rate_limiting",
                "severity": "medium",
                "count": len(rate_limit_events),
                "description": f"Rate limits exceeded {len(rate_limit_events)} times"
            })
        
        return anomalies
    
    async def _periodic_flush(self):
        """Periodically flush logs to prevent memory buildup."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_logs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in periodic log flush: {e}")
    
    async def _flush_logs(self):
        """Flush logs to persistent storage."""
        if not self.log_buffer:
            return
        
        # In a production system, this would write to a logging database,
        # file system, or external logging service like ELK stack
        
        # For now, we'll just print critical events and clear the buffer
        critical_events = [
            entry for entry in self.log_buffer 
            if entry.severity == Severity.CRITICAL
        ]
        
        if critical_events:
            print(f"🚨 CRITICAL EVENTS: {len(critical_events)} critical activities logged")
            for event in critical_events:
                print(f"   - {event.activity_type.value}: {event.details}")
        
        # Clear the buffer
        flushed_count = len(self.log_buffer)
        self.log_buffer.clear()
        
        if flushed_count > 0:
            print(f"📝 Flushed {flushed_count} activity log entries")


# Global activity logger instance
_activity_logger: Optional[ActivityLogger] = None


def get_activity_logger() -> ActivityLogger:
    """Get the global activity logger instance."""
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ActivityLogger()
    return _activity_logger


async def start_activity_logging():
    """Start the activity logging service."""
    logger = get_activity_logger()
    await logger.start()


async def stop_activity_logging():
    """Stop the activity logging service."""
    logger = get_activity_logger()
    await logger.stop()


# Convenience functions for common logging operations
async def log_api_key_created(api_key_id: str, user_id: str, key_name: str, scopes: List[str], **kwargs):
    """Log API key creation."""
    logger = get_activity_logger()
    await logger.log_key_creation(api_key_id, user_id, key_name, scopes, **kwargs)


async def log_auth_attempt(api_key_id: Optional[str], success: bool, **kwargs):
    """Log authentication attempt."""
    logger = get_activity_logger()
    await logger.log_authentication_attempt(api_key_id, success, **kwargs)


async def log_rate_limit_event(api_key_id: str, event_type: str, limit: int, usage: int, **kwargs):
    """Log rate limiting event."""
    logger = get_activity_logger()
    await logger.log_rate_limit_event(api_key_id, event_type, limit, usage, **kwargs)


async def log_security_event(event_type: str, severity: Severity, **kwargs):
    """Log security event."""
    logger = get_activity_logger()
    await logger.log_security_event(event_type, severity, **kwargs)


async def log_admin_action(admin_user_id: str, action: str, target_resource: str, **kwargs):
    """Log administrative action."""
    logger = get_activity_logger()
    await logger.log_admin_action(admin_user_id, action, target_resource, **kwargs)