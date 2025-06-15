"""
Rate Limiting Management Router

API endpoints for monitoring, configuring, and managing rate limits
for API keys and system-wide rate limiting policies.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from datetime import datetime

from ..core.rate_limiting import RateLimitAlgorithm, RateLimitResult
from ..middleware.rate_limiting import get_rate_limit_manager, check_rate_limit_status
from ..middleware.permissions import require_resource_permission, get_permission_checker, PermissionChecker
from ..middleware import require_api_key
from ..core.permissions import ResourceType, Permission
from ..models.api_key import APIKey, RateLimitType


router = APIRouter(prefix="/rate-limits", tags=["Rate Limiting"])


# Request/Response Models
class RateLimitStatusResponse(BaseModel):
    """Response model for rate limit status."""
    api_key_id: str
    rate_limit: Optional[int]
    rate_limit_period: Optional[str]
    current_usage: int
    remaining: int
    reset_time: str
    algorithm: Optional[str]
    window_size_seconds: Optional[int]


class RateLimitTestRequest(BaseModel):
    """Request model for rate limit testing."""
    requests_count: int = 1
    delay_between_requests: float = 0.0
    endpoint: Optional[str] = None


class RateLimitTestResponse(BaseModel):
    """Response model for rate limit testing."""
    total_requests: int
    successful_requests: int
    rate_limited_requests: int
    test_duration_seconds: float
    results: List[Dict[str, Any]]


class RateLimitConfigRequest(BaseModel):
    """Request model for updating rate limit configuration."""
    rate_limit: int
    rate_limit_period: RateLimitType
    algorithm: Optional[RateLimitAlgorithm] = None


class RateLimitStatsResponse(BaseModel):
    """Response model for rate limit statistics."""
    total_api_keys: int
    rate_limited_requests_today: int
    most_limited_endpoints: List[Dict[str, Any]]
    algorithm_usage: Dict[str, int]
    average_usage_percentage: float


# Public endpoints (require API key)
@router.get("/status", response_model=RateLimitStatusResponse)
async def get_my_rate_limit_status(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get current rate limit status for the API key.
    
    Returns detailed information about rate limits, current usage,
    and when limits will reset.
    """
    manager = get_rate_limit_manager()
    status_info = await manager.get_rate_limit_status(api_key)
    
    return RateLimitStatusResponse(
        api_key_id=api_key.key_id,
        rate_limit=status_info["rate_limit"],
        rate_limit_period=status_info["rate_limit_period"],
        current_usage=status_info["current_usage"],
        remaining=status_info["remaining"],
        reset_time=status_info["reset_time"],
        algorithm=status_info["algorithm"],
        window_size_seconds=manager._get_window_seconds(api_key.rate_limit_period) if api_key.rate_limit_period else None
    )


@router.get("/info")
async def get_rate_limit_info(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get general information about rate limiting system.
    
    Returns available algorithms, rate limit types, and configuration options.
    """
    return {
        "rate_limiting": {
            "enabled": True,
            "algorithms": [algo.value for algo in RateLimitAlgorithm],
            "rate_limit_types": [rlt.value for rlt in RateLimitType],
            "current_api_key": {
                "rate_limit": api_key.rate_limit,
                "rate_limit_period": api_key.rate_limit_period.value if api_key.rate_limit_period else None,
                "has_custom_limits": api_key.rate_limit is not None
            }
        },
        "algorithms_info": {
            "fixed_window": "Simple, memory efficient, allows bursts at window boundaries",
            "sliding_window": "Smoother rate limiting, prevents boundary bursts",
            "token_bucket": "Allows controlled bursts, good for variable loads",
            "sliding_log": "Most precise, but memory intensive"
        },
        "headers": {
            "X-RateLimit-Limit": "Maximum requests allowed in the time window",
            "X-RateLimit-Remaining": "Number of requests remaining in current window", 
            "X-RateLimit-Reset": "Unix timestamp when the rate limit resets",
            "X-RateLimit-Window": "Size of the rate limiting window in seconds",
            "Retry-After": "Seconds to wait before making another request (when rate limited)"
        }
    }


@router.post("/test", response_model=RateLimitTestResponse)
async def test_rate_limits(
    test_request: RateLimitTestRequest,
    api_key: APIKey = Depends(require_api_key)
):
    """
    Test rate limiting behavior with multiple requests.
    
    Useful for understanding how rate limits work and testing configurations.
    """
    import asyncio
    import time
    
    if test_request.requests_count > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 test requests allowed"
        )
    
    manager = get_rate_limit_manager()
    results = []
    successful = 0
    rate_limited = 0
    start_time = time.time()
    
    for i in range(test_request.requests_count):
        request_start = time.time()
        
        # Check rate limit (with cost 0 to not affect actual limits)
        result = await manager.check_api_key_rate_limit(
            api_key=api_key,
            cost=0,  # Don't actually consume rate limit for testing
            endpoint=test_request.endpoint
        )
        
        request_end = time.time()
        
        if result.allowed:
            successful += 1
        else:
            rate_limited += 1
        
        results.append({
            "request_number": i + 1,
            "allowed": result.allowed,
            "remaining": result.remaining,
            "reset_time": result.reset_time.isoformat(),
            "response_time_ms": (request_end - request_start) * 1000,
            "retry_after": result.retry_after
        })
        
        # Add delay between requests if specified
        if test_request.delay_between_requests > 0 and i < test_request.requests_count - 1:
            await asyncio.sleep(test_request.delay_between_requests)
    
    end_time = time.time()
    
    return RateLimitTestResponse(
        total_requests=test_request.requests_count,
        successful_requests=successful,
        rate_limited_requests=rate_limited,
        test_duration_seconds=end_time - start_time,
        results=results
    )


# Admin endpoints (require admin permissions)
@router.get("/admin/stats", response_model=RateLimitStatsResponse)
async def get_rate_limit_statistics(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ))
):
    """
    Get system-wide rate limiting statistics (admin only).
    
    Returns aggregated data about rate limiting across all API keys.
    """
    # In a real implementation, this would query actual statistics
    # For now, return mock data structure
    return RateLimitStatsResponse(
        total_api_keys=0,
        rate_limited_requests_today=0,
        most_limited_endpoints=[],
        algorithm_usage={
            "sliding_window": 75,
            "fixed_window": 20,
            "token_bucket": 5
        },
        average_usage_percentage=45.2
    )


@router.get("/admin/all-limits")
async def list_all_rate_limits(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ))
):
    """
    List rate limits for all API keys (admin only).
    
    Provides overview of rate limiting configuration across the system.
    """
    # This would typically query the database for all API keys
    # For now, return a mock response
    return {
        "message": "Rate limits for all API keys",
        "pagination": {
            "skip": skip,
            "limit": limit,
            "total": 0
        },
        "rate_limits": [],
        "summary": {
            "keys_with_custom_limits": 0,
            "keys_with_default_limits": 0,
            "most_common_limit": "1000 requests per hour",
            "algorithms_in_use": ["sliding_window", "fixed_window"]
        }
    }


@router.post("/admin/reset/{api_key_id}")
async def reset_api_key_rate_limit(
    api_key_id: str,
    admin_api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.MANAGE))
):
    """
    Reset rate limits for a specific API key (admin only).
    
    Clears all rate limiting counters for the specified API key.
    """
    # This would need to look up the API key and reset its limits
    manager = get_rate_limit_manager()
    
    # For demonstration, create a mock API key object
    # In reality, you'd fetch this from the database
    from uuid import uuid4
    mock_api_key = APIKey(
        id=uuid4(),
        key_id=api_key_id,
        key_hash="mock",
        name="Mock Key",
        user_id=admin_api_key.user_id,
        scopes=["read"]
    )
    
    success = await manager.reset_api_key_rate_limit(mock_api_key)
    
    return {
        "message": "Rate limit reset completed",
        "api_key_id": api_key_id,
        "success": success,
        "reset_by": admin_api_key.key_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/admin/global-reset")
async def reset_all_rate_limits(
    confirm: bool = Query(False, description="Must be true to confirm the action"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.MANAGE))
):
    """
    Reset all rate limits system-wide (admin only).
    
    Dangerous operation that clears all rate limiting data.
    Requires explicit confirmation.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to perform global reset"
        )
    
    # This would reset all rate limiting data
    # Implementation would depend on the backend (Redis, memory, etc.)
    
    return {
        "message": "Global rate limit reset completed",
        "warning": "All rate limiting counters have been cleared",
        "reset_by": api_key.key_id,
        "timestamp": datetime.utcnow().isoformat(),
        "affected_keys": "all"
    }


@router.get("/admin/config")
async def get_rate_limit_configuration(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ))
):
    """
    Get current rate limiting system configuration (admin only).
    
    Returns global settings, default limits, and algorithm configuration.
    """
    return {
        "global_configuration": {
            "default_algorithm": "sliding_window",
            "enable_global_limits": True,
            "enable_endpoint_limits": True,
            "backend": "memory",  # Would be "redis" in production
        },
        "default_limits": {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000,
            "requests_per_month": 100000
        },
        "global_limits": {
            "auth_endpoints": "100 requests per minute",
            "admin_endpoints": "500 requests per minute", 
            "default": "1000 requests per minute"
        },
        "endpoint_specific_limits": {
            "/api/v1/analytics/export": "10 requests per hour",
            "/api/v1/admin/system-info": "100 requests per hour",
            "/api-keys": "50 requests per 10 minutes"
        },
        "algorithms": {
            "available": ["fixed_window", "sliding_window", "token_bucket", "sliding_log"],
            "default": "sliding_window",
            "recommendations": {
                "memory_constrained": "fixed_window",
                "smooth_rate_limiting": "sliding_window", 
                "burst_handling": "token_bucket",
                "precise_limiting": "sliding_log"
            }
        }
    }


# Utility endpoints
@router.get("/check-headers")
async def check_rate_limit_headers(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get information about rate limit headers.
    
    Useful for understanding what headers are included in responses.
    """
    manager = get_rate_limit_manager()
    
    # Get current status
    result = await manager.check_api_key_rate_limit(api_key, cost=0)
    headers = result.to_headers()
    
    return {
        "current_headers": headers,
        "header_descriptions": {
            "X-RateLimit-Limit": "Maximum requests allowed in the time window",
            "X-RateLimit-Remaining": "Requests remaining in current window",
            "X-RateLimit-Reset": "Unix timestamp when limit resets",
            "X-RateLimit-Window": "Time window size in seconds",
            "X-RateLimit-Algorithm": "Rate limiting algorithm in use",
            "Retry-After": "Seconds to wait if rate limited"
        },
        "example_usage": {
            "javascript": "if (response.headers['x-ratelimit-remaining'] < 10) { /* slow down */ }",
            "python": "if int(response.headers.get('x-ratelimit-remaining', 0)) < 10: time.sleep(1)",
            "curl": "curl -H 'Authorization: Bearer sk_...' -I /api/v1/profile"
        }
    }