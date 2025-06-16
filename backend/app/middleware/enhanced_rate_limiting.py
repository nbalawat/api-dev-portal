"""
Enhanced Rate Limiting Middleware.

This middleware provides advanced rate limiting capabilities using token bucket algorithm
and integrates with the existing rate limiting system.
"""
import time
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.enhanced_rate_limiting import enhanced_rate_limit_manager, RateLimitScope


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with token bucket algorithm."""
    
    def __init__(
        self,
        app,
        enable_global_limits: bool = True,
        enable_user_limits: bool = True,
        enable_api_key_limits: bool = True,
        enable_ip_limits: bool = True,
        skip_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.enable_global_limits = enable_global_limits
        self.enable_user_limits = enable_user_limits
        self.enable_api_key_limits = enable_api_key_limits
        self.enable_ip_limits = enable_ip_limits
        self.skip_paths = skip_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next):
        """Process request through enhanced rate limiting."""
        # Skip rate limiting for certain paths
        if self._should_skip_path(request.url.path):
            return await call_next(request)
        
        # Extract identifiers
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)
        api_key_id = self._get_api_key_id(request)
        
        # Prepare rate limit checks
        checks = []
        
        # Global rate limiting
        if self.enable_global_limits:
            checks.append(("global_requests", "system", 1))
        
        # IP-based rate limiting
        if self.enable_ip_limits and client_ip:
            checks.append(("ip_requests", client_ip, 1))
        
        # User-based rate limiting
        if self.enable_user_limits and user_id:
            checks.append(("user_requests", user_id, 1))
        
        # API key-based rate limiting
        if self.enable_api_key_limits and api_key_id:
            checks.append(("api_key_requests", api_key_id, 1))
        
        # Check all rate limits
        if checks:
            results = await enhanced_rate_limit_manager.check_multiple_limits(checks)
            
            # Find the most restrictive limit that was exceeded
            violated_result = None
            for result in results:
                if not result.allowed:
                    violated_result = result
                    break
            
            if violated_result:
                # Rate limit exceeded - return appropriate response
                response_data = {
                    "error": "Rate limit exceeded",
                    "message": f"Rate limit exceeded for {violated_result.scope.value}",
                    "rule": violated_result.rule_name,
                    "retry_after": violated_result.retry_after,
                    "reset_time": violated_result.reset_time
                }
                
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=response_data
                )
                
                # Add rate limit headers
                self._add_rate_limit_headers(response, violated_result)
                return response
        
        # Process the request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add rate limit headers to successful responses
        if checks:
            # Get current status for the most specific limit
            primary_result = results[-1] if results else None
            if primary_result:
                self._add_rate_limit_headers(response, primary_result)
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    def _should_skip_path(self, path: str) -> bool:
        """Check if the path should skip rate limiting."""
        return any(skip_path in path for skip_path in self.skip_paths)
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request."""
        # Check for forwarded headers (when behind a proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return None
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request (from auth context)."""
        # Check if user is available in request state (set by auth middleware)
        if hasattr(request.state, "user") and request.state.user:
            return str(request.state.user.id)
        
        # Try to extract from JWT token in Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # This is a simplified extraction - in practice, you'd decode the JWT
                # For now, we'll extract user info from the existing auth middleware
                pass
            except Exception:
                pass
        
        return None
    
    def _get_api_key_id(self, request: Request) -> Optional[str]:
        """Extract API key ID from request."""
        # Check if API key is available in request state (set by API key auth middleware)
        if hasattr(request.state, "api_key") and request.state.api_key:
            return str(request.state.api_key.id)
        
        # Try to extract from X-API-Key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header:
            return api_key_header[:16]  # Use first 16 chars as identifier
        
        return None
    
    def _add_rate_limit_headers(self, response: Response, result) -> None:
        """Add rate limit headers to response."""
        response.headers["X-RateLimit-Limit"] = str(int(result.current_rate or 0))
        response.headers["X-RateLimit-Remaining"] = str(int(result.tokens_remaining))
        response.headers["X-RateLimit-Reset"] = str(int(result.reset_time))
        response.headers["X-RateLimit-Scope"] = result.scope.value
        
        if result.retry_after:
            response.headers["Retry-After"] = str(int(result.retry_after))


def get_enhanced_rate_limit_manager():
    """Get the global enhanced rate limit manager instance."""
    return enhanced_rate_limit_manager