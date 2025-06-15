"""
API Key Usage Analytics System

Advanced analytics engine for tracking, analyzing, and reporting
API key usage patterns, performance metrics, and business insights.
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.sql import text

from ..models.api_key import APIKey, APIKeyUsage, APIKeyStatus
from ..models.user import User


class AnalyticsTimeframe(str, Enum):
    """Analytics timeframe options."""
    HOUR = "hour"
    DAY = "day" 
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """Types of metrics to calculate."""
    REQUESTS = "requests"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    BANDWIDTH = "bandwidth"
    UNIQUE_IPS = "unique_ips"
    ENDPOINT_POPULARITY = "endpoint_popularity"
    SUCCESS_RATE = "success_rate"


@dataclass
class AnalyticsFilter:
    """Filter options for analytics queries."""
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


@dataclass
class UsageMetric:
    """Container for a usage metric."""
    name: str
    value: float
    unit: str
    timeframe: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AnalyticsReport:
    """Container for analytics report data."""
    title: str
    timeframe: AnalyticsTimeframe
    start_date: datetime
    end_date: datetime
    total_requests: int
    unique_api_keys: int
    unique_users: int
    metrics: List[UsageMetric]
    charts: Dict[str, Any]
    insights: List[str]
    generated_at: datetime


class APIUsageAnalytics:
    """Core analytics engine for API usage data."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_usage_summary(
        self,
        timeframe: AnalyticsTimeframe,
        filters: Optional[AnalyticsFilter] = None
    ) -> Dict[str, Any]:
        """Get high-level usage summary."""
        start_date, end_date = self._get_timeframe_dates(timeframe, filters)
        
        # Build base query
        query = select(APIKeyUsage).where(
            and_(
                APIKeyUsage.timestamp >= start_date,
                APIKeyUsage.timestamp <= end_date
            )
        )
        
        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)
        
        # Execute query to get all usage records
        result = await self.db.execute(query)
        usage_records = result.scalars().all()
        
        # Calculate summary metrics
        total_requests = len(usage_records)
        unique_api_keys = len(set(record.api_key_id for record in usage_records))
        unique_ips = len(set(record.ip_address for record in usage_records if record.ip_address))
        
        # Calculate response time metrics
        response_times = [r.response_time_ms for r in usage_records if r.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate error rate
        error_count = len([r for r in usage_records if r.status_code >= 400])
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate bandwidth
        total_request_bytes = sum(r.request_size_bytes or 0 for r in usage_records)
        total_response_bytes = sum(r.response_size_bytes or 0 for r in usage_records)
        
        return {
            "timeframe": timeframe.value,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_requests": total_requests,
                "unique_api_keys": unique_api_keys,
                "unique_ip_addresses": unique_ips,
                "average_response_time_ms": round(avg_response_time, 2),
                "error_rate_percent": round(error_rate, 2),
                "total_bandwidth_bytes": total_request_bytes + total_response_bytes
            },
            "bandwidth": {
                "total_request_bytes": total_request_bytes,
                "total_response_bytes": total_response_bytes,
                "average_request_size_bytes": total_request_bytes / total_requests if total_requests > 0 else 0,
                "average_response_size_bytes": total_response_bytes / total_requests if total_requests > 0 else 0
            }
        }
    
    async def get_time_series_data(
        self,
        metric: MetricType,
        timeframe: AnalyticsTimeframe,
        interval: str = "hour",
        filters: Optional[AnalyticsFilter] = None
    ) -> List[Dict[str, Any]]:
        """Get time series data for a specific metric."""
        start_date, end_date = self._get_timeframe_dates(timeframe, filters)
        
        # Create time buckets based on interval
        time_buckets = self._create_time_buckets(start_date, end_date, interval)
        
        # Build query
        query = select(APIKeyUsage).where(
            and_(
                APIKeyUsage.timestamp >= start_date,
                APIKeyUsage.timestamp <= end_date
            )
        )
        
        if filters:
            query = self._apply_filters(query, filters)
        
        result = await self.db.execute(query)
        usage_records = result.scalars().all()
        
        # Group data by time buckets
        bucket_data = defaultdict(list)
        for record in usage_records:
            bucket_key = self._get_time_bucket_key(record.timestamp, interval)
            bucket_data[bucket_key].append(record)
        
        # Calculate metric values for each bucket
        time_series = []
        for bucket_time in time_buckets:
            bucket_key = self._get_time_bucket_key(bucket_time, interval)
            records = bucket_data.get(bucket_key, [])
            
            value = self._calculate_metric_value(metric, records)
            
            time_series.append({
                "timestamp": bucket_time.isoformat(),
                "value": value,
                "record_count": len(records)
            })
        
        return time_series
    
    async def get_endpoint_analytics(
        self,
        timeframe: AnalyticsTimeframe,
        filters: Optional[AnalyticsFilter] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get analytics for individual endpoints."""
        start_date, end_date = self._get_timeframe_dates(timeframe, filters)
        
        query = select(APIKeyUsage).where(
            and_(
                APIKeyUsage.timestamp >= start_date,
                APIKeyUsage.timestamp <= end_date
            )
        )
        
        if filters:
            query = self._apply_filters(query, filters)
        
        result = await self.db.execute(query)
        usage_records = result.scalars().all()
        
        # Group by endpoint
        endpoint_data = defaultdict(list)
        for record in usage_records:
            endpoint_data[record.endpoint].append(record)
        
        # Calculate metrics for each endpoint
        endpoint_analytics = []
        for endpoint, records in endpoint_data.items():
            total_requests = len(records)
            error_count = len([r for r in records if r.status_code >= 400])
            response_times = [r.response_time_ms for r in records if r.response_time_ms]
            
            analytics = {
                "endpoint": endpoint,
                "total_requests": total_requests,
                "error_count": error_count,
                "error_rate_percent": (error_count / total_requests * 100) if total_requests > 0 else 0,
                "average_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "unique_api_keys": len(set(r.api_key_id for r in records)),
                "unique_ips": len(set(r.ip_address for r in records if r.ip_address)),
                "methods": list(set(r.method for r in records)),
                "total_bandwidth_bytes": sum((r.request_size_bytes or 0) + (r.response_size_bytes or 0) for r in records)
            }
            endpoint_analytics.append(analytics)
        
        # Sort by total requests descending
        endpoint_analytics.sort(key=lambda x: x["total_requests"], reverse=True)
        
        return endpoint_analytics[:limit]
    
    async def get_api_key_analytics(
        self,
        api_key_id: str,
        timeframe: AnalyticsTimeframe,
        filters: Optional[AnalyticsFilter] = None
    ) -> Dict[str, Any]:
        """Get detailed analytics for a specific API key."""
        start_date, end_date = self._get_timeframe_dates(timeframe, filters)
        
        # Get API key info
        api_key_query = select(APIKey).where(APIKey.id == api_key_id)
        api_key_result = await self.db.execute(api_key_query)
        api_key = api_key_result.scalar_one_or_none()
        
        if not api_key:
            return {"error": "API key not found"}
        
        # Get usage data
        query = select(APIKeyUsage).where(
            and_(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
                APIKeyUsage.timestamp <= end_date
            )
        )
        
        if filters:
            query = self._apply_filters(query, filters)
        
        result = await self.db.execute(query)
        usage_records = result.scalars().all()
        
        # Calculate comprehensive metrics
        total_requests = len(usage_records)
        error_count = len([r for r in usage_records if r.status_code >= 400])
        response_times = [r.response_time_ms for r in usage_records if r.response_time_ms]
        
        # Group by time periods for trends
        daily_usage = defaultdict(int)
        hourly_usage = defaultdict(int)
        
        for record in usage_records:
            day_key = record.timestamp.date().isoformat()
            hour_key = record.timestamp.strftime("%Y-%m-%d %H:00")
            daily_usage[day_key] += 1
            hourly_usage[hour_key] += 1
        
        # Top endpoints
        endpoint_counts = defaultdict(int)
        for record in usage_records:
            endpoint_counts[record.endpoint] += 1
        
        top_endpoints = sorted(
            endpoint_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "api_key_info": {
                "key_id": api_key.key_id,
                "name": api_key.name,
                "status": api_key.status.value,
                "created_at": api_key.created_at.isoformat(),
                "scopes": api_key.scopes
            },
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "metrics": {
                "total_requests": total_requests,
                "error_count": error_count,
                "error_rate_percent": (error_count / total_requests * 100) if total_requests > 0 else 0,
                "average_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "unique_endpoints": len(set(r.endpoint for r in usage_records)),
                "unique_ips": len(set(r.ip_address for r in usage_records if r.ip_address))
            },
            "trends": {
                "daily_usage": dict(daily_usage),
                "hourly_usage": dict(hourly_usage),
                "peak_hour": max(hourly_usage.items(), key=lambda x: x[1])[0] if hourly_usage else None,
                "peak_day": max(daily_usage.items(), key=lambda x: x[1])[0] if daily_usage else None
            },
            "top_endpoints": [{"endpoint": ep, "requests": count} for ep, count in top_endpoints]
        }
    
    async def get_user_analytics(
        self,
        user_id: str,
        timeframe: AnalyticsTimeframe,
        filters: Optional[AnalyticsFilter] = None
    ) -> Dict[str, Any]:
        """Get analytics for all API keys belonging to a user."""
        start_date, end_date = self._get_timeframe_dates(timeframe, filters)
        
        # Get user's API keys
        api_keys_query = select(APIKey).where(APIKey.user_id == user_id)
        api_keys_result = await self.db.execute(api_keys_query)
        user_api_keys = api_keys_result.scalars().all()
        
        if not user_api_keys:
            return {"error": "No API keys found for user"}
        
        api_key_ids = [str(key.id) for key in user_api_keys]
        
        # Get usage data for all user's API keys
        query = select(APIKeyUsage).where(
            and_(
                APIKeyUsage.api_key_id.in_(api_key_ids),
                APIKeyUsage.timestamp >= start_date,
                APIKeyUsage.timestamp <= end_date
            )
        )
        
        if filters:
            query = self._apply_filters(query, filters)
        
        result = await self.db.execute(query)
        usage_records = result.scalars().all()
        
        # Calculate metrics per API key
        api_key_metrics = {}
        for api_key in user_api_keys:
            key_records = [r for r in usage_records if str(r.api_key_id) == str(api_key.id)]
            api_key_metrics[api_key.key_id] = {
                "name": api_key.name,
                "requests": len(key_records),
                "errors": len([r for r in key_records if r.status_code >= 400]),
                "last_used": max((r.timestamp for r in key_records), default=None)
            }
        
        # Overall user metrics
        total_requests = len(usage_records)
        error_count = len([r for r in usage_records if r.status_code >= 400])
        
        return {
            "user_id": user_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_api_keys": len(user_api_keys),
                "active_api_keys": len([k for k in user_api_keys if k.status == APIKeyStatus.active]),
                "total_requests": total_requests,
                "error_rate_percent": (error_count / total_requests * 100) if total_requests > 0 else 0
            },
            "api_key_breakdown": api_key_metrics
        }
    
    async def generate_insights(
        self,
        timeframe: AnalyticsTimeframe,
        filters: Optional[AnalyticsFilter] = None
    ) -> List[str]:
        """Generate actionable insights from usage data."""
        insights = []
        
        # Get usage summary for analysis
        summary = await self.get_usage_summary(timeframe, filters)
        
        # Insight 1: High error rate
        error_rate = summary["summary"]["error_rate_percent"]
        if error_rate > 10:
            insights.append(f"High error rate detected: {error_rate:.1f}%. Consider reviewing API implementations.")
        elif error_rate < 1:
            insights.append(f"Excellent error rate: {error_rate:.1f}%. API stability is very good.")
        
        # Insight 2: Response time analysis
        avg_response_time = summary["summary"]["average_response_time_ms"]
        if avg_response_time > 1000:
            insights.append(f"Slow response times detected: {avg_response_time:.0f}ms average. Consider performance optimization.")
        elif avg_response_time < 100:
            insights.append(f"Excellent response times: {avg_response_time:.0f}ms average.")
        
        # Insight 3: Usage patterns
        total_requests = summary["summary"]["total_requests"]
        if total_requests == 0:
            insights.append("No API usage detected in this timeframe.")
        elif total_requests > 10000:
            insights.append(f"High API usage: {total_requests:,} requests. Consider implementing caching strategies.")
        
        # Get endpoint analytics for more insights
        endpoint_data = await self.get_endpoint_analytics(timeframe, filters, limit=10)
        
        if endpoint_data:
            # Most popular endpoint
            top_endpoint = endpoint_data[0]
            insights.append(f"Most popular endpoint: {top_endpoint['endpoint']} ({top_endpoint['total_requests']} requests)")
            
            # Endpoints with high error rates
            problematic_endpoints = [ep for ep in endpoint_data if ep["error_rate_percent"] > 15]
            if problematic_endpoints:
                ep_names = [ep["endpoint"] for ep in problematic_endpoints[:3]]
                insights.append(f"Endpoints with high error rates: {', '.join(ep_names)}")
        
        return insights
    
    def _get_timeframe_dates(
        self,
        timeframe: AnalyticsTimeframe,
        filters: Optional[AnalyticsFilter]
    ) -> Tuple[datetime, datetime]:
        """Get start and end dates for a timeframe."""
        now = datetime.utcnow()
        
        if filters and filters.start_date and filters.end_date:
            return filters.start_date, filters.end_date
        
        if timeframe == AnalyticsTimeframe.HOUR:
            start = now - timedelta(hours=1)
        elif timeframe == AnalyticsTimeframe.DAY:
            start = now - timedelta(days=1)
        elif timeframe == AnalyticsTimeframe.WEEK:
            start = now - timedelta(weeks=1)
        elif timeframe == AnalyticsTimeframe.MONTH:
            start = now - timedelta(days=30)
        elif timeframe == AnalyticsTimeframe.QUARTER:
            start = now - timedelta(days=90)
        elif timeframe == AnalyticsTimeframe.YEAR:
            start = now - timedelta(days=365)
        else:
            start = now - timedelta(days=7)  # Default to week
        
        return start, now
    
    def _apply_filters(self, query, filters: AnalyticsFilter):
        """Apply filters to a query."""
        if filters.api_key_ids:
            query = query.where(APIKeyUsage.api_key_id.in_(filters.api_key_ids))
        
        if filters.endpoints:
            query = query.where(APIKeyUsage.endpoint.in_(filters.endpoints))
        
        if filters.methods:
            query = query.where(APIKeyUsage.method.in_(filters.methods))
        
        if filters.status_codes:
            query = query.where(APIKeyUsage.status_code.in_(filters.status_codes))
        
        if filters.ip_addresses:
            query = query.where(APIKeyUsage.ip_address.in_(filters.ip_addresses))
        
        if filters.min_response_time:
            query = query.where(APIKeyUsage.response_time_ms >= filters.min_response_time)
        
        if filters.max_response_time:
            query = query.where(APIKeyUsage.response_time_ms <= filters.max_response_time)
        
        return query
    
    def _create_time_buckets(self, start_date: datetime, end_date: datetime, interval: str) -> List[datetime]:
        """Create time buckets for time series data."""
        buckets = []
        current = start_date
        
        if interval == "hour":
            delta = timedelta(hours=1)
        elif interval == "day":
            delta = timedelta(days=1)
        elif interval == "week":
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(hours=1)  # Default
        
        while current <= end_date:
            buckets.append(current)
            current += delta
        
        return buckets
    
    def _get_time_bucket_key(self, timestamp: datetime, interval: str) -> str:
        """Get the bucket key for a timestamp."""
        if interval == "hour":
            return timestamp.strftime("%Y-%m-%d %H:00")
        elif interval == "day":
            return timestamp.strftime("%Y-%m-%d")
        elif interval == "week":
            return timestamp.strftime("%Y-W%U")
        else:
            return timestamp.strftime("%Y-%m-%d %H:00")
    
    def _calculate_metric_value(self, metric: MetricType, records: List[APIKeyUsage]) -> float:
        """Calculate the value for a specific metric."""
        if not records:
            return 0.0
        
        if metric == MetricType.REQUESTS:
            return len(records)
        elif metric == MetricType.RESPONSE_TIME:
            response_times = [r.response_time_ms for r in records if r.response_time_ms]
            return sum(response_times) / len(response_times) if response_times else 0
        elif metric == MetricType.ERROR_RATE:
            error_count = len([r for r in records if r.status_code >= 400])
            return (error_count / len(records) * 100) if records else 0
        elif metric == MetricType.BANDWIDTH:
            return sum((r.request_size_bytes or 0) + (r.response_size_bytes or 0) for r in records)
        elif metric == MetricType.UNIQUE_IPS:
            return len(set(r.ip_address for r in records if r.ip_address))
        elif metric == MetricType.SUCCESS_RATE:
            success_count = len([r for r in records if r.status_code < 400])
            return (success_count / len(records) * 100) if records else 0
        else:
            return 0.0