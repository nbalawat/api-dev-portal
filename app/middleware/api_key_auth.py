"""
API Key Authentication Middleware

Middleware to handle API key authentication for protected endpoints.
"""
from typing import Optional, List
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import json

from ..core.api_keys import APIKeyManager
from ..dependencies.database import get_database
from ..models.api_key import APIKey
from ..services.activity_logging import get_activity_logger, log_auth_attempt


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API key authentication.
    
    This middleware checks for API keys in:
    1. Authorization header (Bearer sk_...)
    2. X-API-Key header
    3. Query parameter 'api_key'
    """
    
    # Paths that should be excluded from API key authentication
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/info",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/login",
        "/auth/register",
        "/auth/refresh",
        "/auth/logout"
    }
    
    # Paths that require API key authentication
    API_KEY_PATHS = {
        "/api/v1/",  # All API v1 endpoints
        "/admin/",   # Admin endpoints
    }
    
    def __init__(self, app, enable_for_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.enable_for_paths = enable_for_paths or []
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and check for API key authentication.
        """
        # Record start time for response time calculation
        import time
        request.state.start_time = time.time()
        
        # Skip authentication for excluded paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Check if this path requires API key authentication
        if not self._requires_api_key_auth(request.url.path):
            return await call_next(request)
        
        # Extract API key from request
        api_key = self._extract_api_key(request)
        
        if not api_key:
            # Log failed authentication - no API key provided
            try:
                await log_auth_attempt(
                    api_key_id=None,
                    success=False,
                    source_ip=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    endpoint=request.url.path,
                    failure_reason="API key required"
                )
            except Exception:
                pass  # Don't fail request if logging fails
            
            return self._create_error_response(
                "API key required",
                status.HTTP_401_UNAUTHORIZED
            )
        
        # Validate API key
        try:
            # Get database session
            from ..core.database import async_session
            async with async_session() as db:
                validated_key = await APIKeyManager.validate_api_key(
                    db=db,
                    secret_key=api_key,
                    client_ip=self._get_client_ip(request)
                )
                
                if not validated_key:
                    # Log failed authentication - invalid API key
                    try:
                        await log_auth_attempt(
                            api_key_id=None,  # Don't log invalid key ID
                            success=False,
                            source_ip=self._get_client_ip(request),
                            user_agent=request.headers.get("user-agent"),
                            endpoint=request.url.path,
                            failure_reason="Invalid or expired API key"
                        )
                    except Exception:
                        pass  # Don't fail request if logging fails
                    
                    return self._create_error_response(
                        "Invalid or expired API key",
                        status.HTTP_401_UNAUTHORIZED
                    )
                
                # Add API key info to request state
                request.state.api_key = validated_key
                request.state.authenticated_via = "api_key"
                
                # Log successful authentication
                try:
                    await log_auth_attempt(
                        api_key_id=str(validated_key.id),
                        success=True,
                        source_ip=self._get_client_ip(request),
                        user_agent=request.headers.get("user-agent"),
                        endpoint=request.url.path
                    )
                except Exception:
                    pass  # Don't fail request if logging fails
                
                # Log API usage (will be handled by usage tracking middleware)
                request.state.log_api_usage = True
                
                # Process the request
                response = await call_next(request)
                
                # Log the API usage if successful
                if hasattr(request.state, 'log_api_usage') and request.state.log_api_usage:
                    try:
                        # Use both the old logging method and new usage tracking
                        await APIKeyManager.log_api_usage(
                            db=db,
                            api_key_id=validated_key.id,
                            method=request.method,
                            endpoint=request.url.path,
                            status_code=response.status_code,
                            ip_address=self._get_client_ip(request),
                            user_agent=request.headers.get("user-agent"),
                            request_size_bytes=self._get_request_size(request),
                            response_size_bytes=self._get_response_size(response)
                        )
                        await db.commit()
                        
                        # Also track with the new usage tracking service
                        from ..services.usage_tracking import track_api_request
                        await track_api_request(
                            api_key_id=str(validated_key.id),
                            method=request.method,
                            endpoint=request.url.path,
                            status_code=response.status_code,
                            response_time_ms=self._get_response_time(request),
                            ip_address=self._get_client_ip(request),
                            user_agent=request.headers.get("user-agent"),
                            request_size_bytes=self._get_request_size(request),
                            response_size_bytes=self._get_response_size(response)
                        )
                    except Exception as e:
                        # Don't fail the request if logging fails
                        print(f"Failed to log API usage: {e}")
                
                return response
                
        except Exception as e:
            return self._create_error_response(
                f"Authentication error: {str(e)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _should_skip_auth(self, path: str) -> bool:
        """Check if authentication should be skipped for this path."""
        # Skip for excluded paths
        for excluded_path in self.EXCLUDED_PATHS:
            if path.startswith(excluded_path):
                return True
        return False
    
    def _requires_api_key_auth(self, path: str) -> bool:
        """Check if this path requires API key authentication."""
        # Check if path starts with any API key required paths
        for api_path in self.API_KEY_PATHS:
            if path.startswith(api_path):
                return True
        
        # Check custom enabled paths
        for enabled_path in self.enable_for_paths:
            if path.startswith(enabled_path):
                return True
        
        return False
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from various sources in the request."""
        # 1. Check Authorization header (Bearer sk_...)
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            if token.startswith("sk_"):
                return token
        
        # 2. Check X-API-Key header
        api_key_header = request.headers.get("x-api-key")
        if api_key_header and api_key_header.startswith("sk_"):
            return api_key_header
        
        # 3. Check query parameter
        query_params = request.query_params
        api_key_param = query_params.get("api_key")
        if api_key_param and api_key_param.startswith("sk_"):
            return api_key_param
        
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        forwarded = request.headers.get("x-forwarded")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _get_request_size(self, request: Request) -> Optional[int]:
        """Get request size in bytes."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return None
    
    def _get_response_size(self, response: Response) -> Optional[int]:
        """Get response size in bytes."""
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return None
    
    def _get_response_time(self, request: Request) -> Optional[float]:
        """Get response time from the X-Process-Time header."""
        if hasattr(request, 'state') and hasattr(request.state, 'start_time'):
            import time
            return (time.time() - request.state.start_time) * 1000
        return None
    
    def _create_error_response(self, message: str, status_code: int) -> Response:
        """Create error response for authentication failures."""
        error_response = {
            "detail": message,
            "type": "api_key_authentication_error",
            "status_code": status_code
        }
        
        return Response(
            content=json.dumps(error_response),
            status_code=status_code,
            headers={"content-type": "application/json"}
        )


# Dependency function for getting current API key
async def get_current_api_key(request: Request) -> Optional[APIKey]:
    """
    Dependency to get the current API key from request state.
    
    Returns:
        APIKey object if authenticated via API key, None otherwise
    """
    if hasattr(request.state, 'api_key'):
        return request.state.api_key
    return None


# Dependency function for requiring API key authentication
def require_api_key(request: Request) -> APIKey:
    """
    Dependency that requires API key authentication.
    
    Raises:
        HTTPException: If no valid API key is found
        
    Returns:
        APIKey object
    """
    api_key = getattr(request.state, 'api_key', None)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API key required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return api_key


# Dependency function for requiring specific API key scopes
def require_api_key_scopes(required_scopes: List[str]):
    """
    Dependency factory for requiring specific API key scopes.
    
    Args:
        required_scopes: List of required scopes
        
    Returns:
        Dependency function
    """
    def _require_scopes(api_key: APIKey = Depends(require_api_key)) -> APIKey:
        """Check if API key has required scopes."""
        if not api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key has no scopes assigned"
            )
        
        # Check if API key has all required scopes
        missing_scopes = []
        for scope in required_scopes:
            if not APIKeyManager.has_scope(api_key, scope):
                missing_scopes.append(scope)
        
        if missing_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scopes: {', '.join(missing_scopes)}"
            )
        
        return api_key
    
    return _require_scopes