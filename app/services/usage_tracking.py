"""
Usage Tracking Service

Background service for collecting, processing, and storing API usage data
with real-time metrics aggregation and analytics preprocessing.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ..models.api_key import APIKey, APIKeyUsage
from ..core.database import async_session


logger = logging.getLogger(__name__)


class UsageTracker:
    """Real-time usage tracking and aggregation service."""
    
    def __init__(self, batch_size: int = 100, flush_interval: int = 60):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.usage_buffer: List[Dict[str, Any]] = []
        self.metrics_cache: Dict[str, Any] = {}
        self.running = False
        self.last_flush = datetime.utcnow()
        
        # Real-time metrics
        self.request_count = 0
        self.error_count = 0
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.active_api_keys = set()
        
    async def track_request(
        self,
        api_key_id: str,
        method: str,
        endpoint: str,
        status_code: int,
        response_time_ms: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Track a single API request.
        
        This method is called by the middleware for each request.
        """
        usage_data = {
            "api_key_id": api_key_id,
            "timestamp": datetime.utcnow(),
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_size_bytes": request_size_bytes,
            "response_size_bytes": response_size_bytes,
            "error_code": error_code,
            "error_message": error_message,
            "extra_data": extra_data or {}
        }
        
        # Add to buffer
        self.usage_buffer.append(usage_data)
        
        # Update real-time metrics
        self.request_count += 1
        if status_code >= 400:
            self.error_count += 1
        if response_time_ms:
            self.response_times.append(response_time_ms)
        self.active_api_keys.add(api_key_id)
        
        # Flush if buffer is full
        if len(self.usage_buffer) >= self.batch_size:
            await self.flush_buffer()
    
    async def flush_buffer(self):
        """Flush the usage buffer to database."""
        if not self.usage_buffer:
            return
        
        try:
            async with async_session() as db:
                # Create usage records
                usage_records = []
                for usage_data in self.usage_buffer:
                    usage_record = APIKeyUsage(**usage_data)
                    usage_records.append(usage_record)
                
                # Bulk insert
                db.add_all(usage_records)
                await db.commit()
                
                logger.info(f"Flushed {len(usage_records)} usage records to database")
                
                # Clear buffer
                self.usage_buffer.clear()
                self.last_flush = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Failed to flush usage buffer: {e}")
            # Keep the buffer for retry
    
    async def start_background_tasks(self):
        """Start background tasks for periodic flushing and cleanup."""
        self.running = True
        
        # Start periodic flush task
        asyncio.create_task(self._periodic_flush())
        
        # Start metrics aggregation task
        asyncio.create_task(self._periodic_metrics_aggregation())
        
        logger.info("Usage tracking background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background tasks and flush remaining data."""
        self.running = False
        
        # Final flush
        await self.flush_buffer()
        
        logger.info("Usage tracking background tasks stopped")
    
    async def _periodic_flush(self):
        """Periodically flush the buffer even if not full."""
        while self.running:
            try:
                await asyncio.sleep(self.flush_interval)
                
                # Check if it's time to flush
                if (datetime.utcnow() - self.last_flush).seconds >= self.flush_interval:
                    await self.flush_buffer()
                    
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _periodic_metrics_aggregation(self):
        """Periodically aggregate and cache metrics."""
        while self.running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._update_metrics_cache()
                
            except Exception as e:
                logger.error(f"Error in metrics aggregation: {e}")
    
    async def _update_metrics_cache(self):
        """Update cached metrics from database."""
        try:
            async with async_session() as db:
                now = datetime.utcnow()
                hour_ago = now - timedelta(hours=1)
                day_ago = now - timedelta(days=1)
                
                # Get hourly metrics
                hourly_query = select(
                    func.count(APIKeyUsage.id).label("total_requests"),
                    func.count(APIKeyUsage.id).filter(APIKeyUsage.status_code >= 400).label("error_count"),
                    func.avg(APIKeyUsage.response_time_ms).label("avg_response_time"),
                    func.count(func.distinct(APIKeyUsage.api_key_id)).label("unique_api_keys")
                ).where(APIKeyUsage.timestamp >= hour_ago)
                
                hourly_result = await db.execute(hourly_query)
                hourly_stats = hourly_result.first()
                
                # Get daily metrics
                daily_query = select(
                    func.count(APIKeyUsage.id).label("total_requests"),
                    func.count(APIKeyUsage.id).filter(APIKeyUsage.status_code >= 400).label("error_count"),
                    func.avg(APIKeyUsage.response_time_ms).label("avg_response_time"),
                    func.count(func.distinct(APIKeyUsage.api_key_id)).label("unique_api_keys")
                ).where(APIKeyUsage.timestamp >= day_ago)
                
                daily_result = await db.execute(daily_query)
                daily_stats = daily_result.first()
                
                # Update cache
                self.metrics_cache = {
                    "last_updated": now.isoformat(),
                    "realtime": {
                        "total_requests": self.request_count,
                        "error_count": self.error_count,
                        "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
                        "active_api_keys": len(self.active_api_keys),
                        "buffer_size": len(self.usage_buffer)
                    },
                    "hourly": {
                        "total_requests": hourly_stats.total_requests or 0,
                        "error_count": hourly_stats.error_count or 0,
                        "avg_response_time": float(hourly_stats.avg_response_time or 0),
                        "unique_api_keys": hourly_stats.unique_api_keys or 0,
                        "error_rate": (hourly_stats.error_count / hourly_stats.total_requests * 100) if hourly_stats.total_requests else 0
                    },
                    "daily": {
                        "total_requests": daily_stats.total_requests or 0,
                        "error_count": daily_stats.error_count or 0,
                        "avg_response_time": float(daily_stats.avg_response_time or 0),
                        "unique_api_keys": daily_stats.unique_api_keys or 0,
                        "error_rate": (daily_stats.error_count / daily_stats.total_requests * 100) if daily_stats.total_requests else 0
                    }
                }
                
                logger.debug("Updated metrics cache")
                
        except Exception as e:
            logger.error(f"Failed to update metrics cache: {e}")
    
    def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics."""
        return {
            "realtime_stats": {
                "total_requests": self.request_count,
                "error_count": self.error_count,
                "error_rate": (self.error_count / self.request_count * 100) if self.request_count > 0 else 0,
                "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
                "active_api_keys": len(self.active_api_keys),
                "buffer_size": len(self.usage_buffer),
                "last_flush": self.last_flush.isoformat()
            },
            "cached_metrics": self.metrics_cache
        }
    
    async def get_api_key_metrics(self, api_key_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get metrics for a specific API key."""
        try:
            async with async_session() as db:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                
                query = select(
                    func.count(APIKeyUsage.id).label("total_requests"),
                    func.count(APIKeyUsage.id).filter(APIKeyUsage.status_code >= 400).label("error_count"),
                    func.avg(APIKeyUsage.response_time_ms).label("avg_response_time"),
                    func.min(APIKeyUsage.timestamp).label("first_request"),
                    func.max(APIKeyUsage.timestamp).label("last_request"),
                    func.count(func.distinct(APIKeyUsage.endpoint)).label("unique_endpoints"),
                    func.count(func.distinct(APIKeyUsage.ip_address)).label("unique_ips")
                ).where(
                    and_(
                        APIKeyUsage.api_key_id == api_key_id,
                        APIKeyUsage.timestamp >= cutoff_time
                    )
                )
                
                result = await db.execute(query)
                stats = result.first()
                
                return {
                    "api_key_id": api_key_id,
                    "timeframe_hours": hours,
                    "metrics": {
                        "total_requests": stats.total_requests or 0,
                        "error_count": stats.error_count or 0,
                        "error_rate": (stats.error_count / stats.total_requests * 100) if stats.total_requests else 0,
                        "avg_response_time": float(stats.avg_response_time or 0),
                        "unique_endpoints": stats.unique_endpoints or 0,
                        "unique_ips": stats.unique_ips or 0,
                        "first_request": stats.first_request.isoformat() if stats.first_request else None,
                        "last_request": stats.last_request.isoformat() if stats.last_request else None
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get API key metrics: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_usage_data(self, days: int = 90):
        """Clean up old usage data to manage database size."""
        try:
            async with async_session() as db:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Count records to be deleted
                count_query = select(func.count(APIKeyUsage.id)).where(
                    APIKeyUsage.timestamp < cutoff_date
                )
                count_result = await db.execute(count_query)
                count_to_delete = count_result.scalar()
                
                if count_to_delete > 0:
                    # Delete old records
                    delete_query = select(APIKeyUsage).where(
                        APIKeyUsage.timestamp < cutoff_date
                    )
                    old_records = await db.execute(delete_query)
                    
                    for record in old_records.scalars():
                        await db.delete(record)
                    
                    await db.commit()
                    
                    logger.info(f"Cleaned up {count_to_delete} old usage records (older than {days} days)")
                else:
                    logger.info("No old usage records to clean up")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old usage data: {e}")


class UsageAggregator:
    """Service for aggregating usage data into summary tables."""
    
    def __init__(self):
        self.aggregation_intervals = {
            "hourly": timedelta(hours=1),
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30)
        }
    
    async def aggregate_usage_data(self, interval: str = "hourly"):
        """Aggregate raw usage data into summary tables."""
        if interval not in self.aggregation_intervals:
            raise ValueError(f"Invalid interval: {interval}")
        
        try:
            async with async_session() as db:
                # This would implement actual aggregation logic
                # For now, return a placeholder
                logger.info(f"Aggregating usage data for {interval} interval")
                
                # In a real implementation, this would:
                # 1. Group usage data by time intervals
                # 2. Calculate aggregated metrics (sum, avg, count, etc.)
                # 3. Store in summary tables for faster analytics queries
                # 4. Update materialized views if using them
                
                return {
                    "status": "completed",
                    "interval": interval,
                    "aggregated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to aggregate usage data: {e}")
            raise


# Global usage tracker instance
_usage_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get the global usage tracker instance."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker


async def track_api_request(
    api_key_id: str,
    method: str,
    endpoint: str,
    status_code: int,
    **kwargs
):
    """Convenience function to track an API request."""
    tracker = get_usage_tracker()
    await tracker.track_request(
        api_key_id=api_key_id,
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        **kwargs
    )


async def start_usage_tracking():
    """Start the usage tracking service."""
    tracker = get_usage_tracker()
    await tracker.start_background_tasks()


async def stop_usage_tracking():
    """Stop the usage tracking service."""
    tracker = get_usage_tracker()
    await tracker.stop_background_tasks()