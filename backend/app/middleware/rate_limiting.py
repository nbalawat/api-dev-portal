"""
Rate Limiting Middleware

Middleware that enforces rate limits on API key requests with
configurable algorithms and proper HTTP response handling.
"""
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json
import time

from ..core.rate_limiting import (
    APIKeyRateLimitManager, MemoryRateLimiter, RateLimitAlgorithm,
    RateLimitResult, RateLimitResponse
)
from ..models.api_key import APIKey


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API key requests.
    
    This middleware checks rate limits after API key authentication
    and before the request reaches the endpoint.
    """
    
    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/info", 
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/login",
        "/auth/register"
    }
    
    # Global rate limits (requests per minute)
    GLOBAL_LIMITS = {
        "default": 1000,  # Default global limit
        "auth": 100,      # Authentication endpoints
        "admin": 500,     # Admin endpoints
    }
    
    def __init__(
        self, 
        app,
        rate_limit_manager: Optional[APIKeyRateLimitManager] = None,
        enable_global_limits: bool = True,
        enable_endpoint_limits: bool = True
    ):
        super().__init__(app)
        
        # Initialize rate limit manager with memory backend if not provided
        if rate_limit_manager is None:
            memory_limiter = MemoryRateLimiter(RateLimitAlgorithm.SLIDING_WINDOW)
            rate_limit_manager = APIKeyRateLimitManager(memory_limiter)
        
        self.rate_limit_manager = rate_limit_manager
        self.enable_global_limits = enable_global_limits
        self.enable_endpoint_limits = enable_endpoint_limits
    
    async def dispatch(self, request: Request, call_next):
        """Process request and enforce rate limits."""
        # Skip rate limiting for excluded paths
        if self._should_skip_rate_limiting(request.url.path):
            return await call_next(request)
        
        # Only apply rate limiting if API key is present
        api_key = getattr(request.state, 'api_key', None)
        if not api_key:
            return await call_next(request)
        
        # Check API key rate limit
        rate_limit_result = await self._check_api_key_rate_limit(request, api_key)
        
        if not rate_limit_result.allowed:
            return self._create_rate_limit_response(rate_limit_result)
        
        # Check global rate limits if enabled
        if self.enable_global_limits:
            global_result = await self._check_global_rate_limits(request, api_key)
            if global_result and not global_result.allowed:
                return self._create_rate_limit_response(global_result, is_global=True)
        
        # Check endpoint-specific rate limits if enabled
        if self.enable_endpoint_limits:
            endpoint_result = await self._check_endpoint_rate_limits(request)
            if endpoint_result and not endpoint_result.allowed:
                return self._create_rate_limit_response(endpoint_result, is_endpoint=True)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        self._add_rate_limit_headers(response, rate_limit_result)
        
        return response
    
    def _should_skip_rate_limiting(self, path: str) -> bool:
        """Check if rate limiting should be skipped for this path."""
        for excluded_path in self.EXCLUDED_PATHS:
            if path.startswith(excluded_path):
                return True
        return False
    
    async def _check_api_key_rate_limit(
        self, 
        request: Request, 
        api_key: APIKey
    ) -> RateLimitResult:
        """Check rate limit for the API key."""
        # Calculate request cost based on method and content
        cost = self._calculate_request_cost(request)
        
        # Check API key rate limit
        return await self.rate_limit_manager.check_api_key_rate_limit(
            api_key=api_key,
            cost=cost,
            endpoint=request.url.path
        )
    
    async def _check_global_rate_limits(
        self, 
        request: Request, 
        api_key: APIKey
    ) -> Optional[RateLimitResult]:
        """Check global rate limits for the user."""
        # Determine which global limit to apply
        path = request.url.path
        
        if path.startswith("/auth/"):
            limit_type = "auth"
        elif path.startswith("/admin/"):
            limit_type = "admin"
        else:
            limit_type = "default"
        
        limit = self.GLOBAL_LIMITS.get(limit_type, self.GLOBAL_LIMITS["default"])
        
        return await self.rate_limit_manager.check_global_rate_limit(
            user_id=str(api_key.user_id),
            limit=limit,
            window_seconds=60,  # 1 minute window
            cost=1
        )
    
    async def _check_endpoint_rate_limits(
        self, 
        request: Request
    ) -> Optional[RateLimitResult]:
        """Check endpoint-specific rate limits."""
        # Define endpoint-specific limits
        endpoint_limits = {
            "/api/v1/analytics/export": (10, 3600),    # 10 requests per hour
            "/api/v1/admin/system-info": (100, 3600),  # 100 requests per hour
            "/api-keys": (50, 600),                     # 50 requests per 10 minutes
        }
        
        path = request.url.path
        
        # Check for matching endpoint patterns
        for endpoint_pattern, (limit, window) in endpoint_limits.items():
            if path.startswith(endpoint_pattern):
                return await self.rate_limit_manager.check_endpoint_rate_limit(
                    endpoint=endpoint_pattern,
                    limit=limit,
                    window_seconds=window,
                    cost=1
                )
        
        return None
    
    def _calculate_request_cost(self, request: Request) -> int:
        """Calculate the cost of a request for rate limiting."""
        method = request.method
        path = request.url.path
        
        # Different costs for different operations
        if method == "GET":
            if "/analytics/" in path or "/admin/" in path:
                return 2  # Analytics and admin reads are more expensive
            return 1  # Regular reads
        elif method in ["POST", "PUT", "PATCH"]:
            if "/admin/" in path:
                return 5  # Admin writes are expensive
            elif path.endswith("/bulk-operation"):
                return 10  # Bulk operations are very expensive
            return 3  # Regular writes
        elif method == "DELETE":
            return 5  # Deletes are expensive
        else:
            return 1  # Default cost
    
    def _add_rate_limit_headers(self, response: Response, result: RateLimitResult):
        """Add rate limit headers to the response."""
        headers = result.to_headers()
        for key, value in headers.items():
            response.headers[key] = value
    
    def _create_rate_limit_response(
        self, 
        result: RateLimitResult, 
        is_global: bool = False,
        is_endpoint: bool = False
    ) -> JSONResponse:
        """Create a rate limit exceeded response."""
        error_type = "rate_limit_exceeded"
        if is_global:
            error_type = "global_rate_limit_exceeded"
        elif is_endpoint:
            error_type = "endpoint_rate_limit_exceeded"
        
        error_response = {
            "error": error_type,
            "message": "Rate limit exceeded",
            "details": {
                "limit": result.limit,
                "remaining": result.remaining,
                "reset_time": result.reset_time.isoformat(),
                "retry_after": result.retry_after,
                "algorithm": result.algorithm
            }
        }
        
        # Add helpful information
        if result.window_size:
            error_response["details"]["window_size"] = result.window_size
        
        if result.retry_after:
            error_response["details"]["retry_after_seconds"] = result.retry_after
        
        response = JSONResponse(
            content=error_response,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
        
        # Add rate limit headers
        headers = result.to_headers()
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# Dependency functions for checking rate limits in endpoints
async def check_rate_limit_status(request: Request) -> Dict[str, Any]:
    """
    Dependency to get current rate limit status.
    
    Returns rate limit information without affecting the limits.
    """
    api_key = getattr(request.state, 'api_key', None)
    if not api_key:
        return {"rate_limiting": "not_applicable", "reason": "no_api_key"}
    
    # Create a temporary rate limit manager for status checking
    memory_limiter = MemoryRateLimiter(RateLimitAlgorithm.SLIDING_WINDOW)
    manager = APIKeyRateLimitManager(memory_limiter)
    
    status_info = await manager.get_rate_limit_status(api_key)
    
    return {
        "rate_limiting": "active",
        "status": status_info,
        "headers_info": {
            "X-RateLimit-Limit": "Current rate limit",
            "X-RateLimit-Remaining": "Remaining requests in window",
            "X-RateLimit-Reset": "Unix timestamp when limit resets",
            "Retry-After": "Seconds to wait if rate limited"
        }
    }


class RateLimitConfig:
    """Configuration for rate limiting."""
    
    def __init__(
        self,
        algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW,
        enable_global_limits: bool = True,
        enable_endpoint_limits: bool = True,
        redis_url: Optional[str] = None,
        default_limits: Optional[Dict[str, int]] = None
    ):
        self.algorithm = algorithm
        self.enable_global_limits = enable_global_limits
        self.enable_endpoint_limits = enable_endpoint_limits
        self.redis_url = redis_url
        self.default_limits = default_limits or {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000
        }
    
    def create_rate_limit_manager(self) -> APIKeyRateLimitManager:
        """Create a rate limit manager based on configuration."""
        if self.redis_url:
            try:
                import redis.asyncio as redis
                redis_client = redis.from_url(self.redis_url)
                from ..core.rate_limiting import RedisRateLimiter
                rate_limiter = RedisRateLimiter(redis_client, self.algorithm)
            except ImportError:
                # Fallback to memory if Redis is not available
                rate_limiter = MemoryRateLimiter(self.algorithm)
        else:
            rate_limiter = MemoryRateLimiter(self.algorithm)
        
        return APIKeyRateLimitManager(rate_limiter)


# Global rate limit manager instance
_rate_limit_manager: Optional[APIKeyRateLimitManager] = None


def get_rate_limit_manager() -> APIKeyRateLimitManager:
    """Get the global rate limit manager instance."""
    global _rate_limit_manager
    if _rate_limit_manager is None:
        # Initialize with memory backend
        memory_limiter = MemoryRateLimiter(RateLimitAlgorithm.SLIDING_WINDOW)
        _rate_limit_manager = APIKeyRateLimitManager(memory_limiter)
    return _rate_limit_manager


def set_rate_limit_manager(manager: APIKeyRateLimitManager):
    """Set the global rate limit manager instance."""
    global _rate_limit_manager
    _rate_limit_manager = manager