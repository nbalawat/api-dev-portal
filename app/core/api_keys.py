"""
API Key generation, validation, and management utilities.
"""
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_

from ..models.api_key import APIKey, APIKeyStatus, APIKeyScope, RateLimitType, APIKeyUsage
from ..models.user import User
from ..core.config import settings


class APIKeyManager:
    """Utility class for managing API keys."""
    
    @staticmethod
    def generate_key_pair() -> Tuple[str, str, str]:
        """
        Generate a new API key pair.
        
        Returns:
            Tuple of (key_id, secret_key, key_hash)
        """
        # Generate key ID (public identifier)
        key_id = f"ak_{secrets.token_urlsafe(16)}"
        
        # Generate secret key
        secret_key = f"sk_{secrets.token_urlsafe(32)}"
        
        # Create hash of the secret key for storage
        key_hash = APIKeyManager.hash_key(secret_key)
        
        return key_id, secret_key, key_hash
    
    @staticmethod
    def hash_key(secret_key: str) -> str:
        """
        Hash an API key for secure storage.
        
        Args:
            secret_key: The secret key to hash
            
        Returns:
            Hashed key suitable for database storage
        """
        # Use HMAC-SHA256 with application secret
        return hmac.new(
            settings.jwt_secret_key.encode(),
            secret_key.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_key(secret_key: str, stored_hash: str) -> bool:
        """
        Verify an API key against its stored hash.
        
        Args:
            secret_key: The provided secret key
            stored_hash: The stored hash from database
            
        Returns:
            True if key is valid, False otherwise
        """
        computed_hash = APIKeyManager.hash_key(secret_key)
        return hmac.compare_digest(computed_hash, stored_hash)
    
    @staticmethod
    async def validate_api_key(
        db: AsyncSession,
        secret_key: str,
        required_scopes: Optional[List[str]] = None,
        client_ip: Optional[str] = None
    ) -> Optional[APIKey]:
        """
        Validate an API key and check permissions.
        
        Args:
            db: Database session
            secret_key: The API key to validate
            required_scopes: Required scopes for the operation
            client_ip: Client IP address for IP restriction checking
            
        Returns:
            APIKey object if valid, None otherwise
        """
        if not secret_key or not secret_key.startswith('sk_'):
            return None
        
        # Get all active API keys
        result = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.status == APIKeyStatus.active,
                    # Only check non-expired keys
                    (APIKey.expires_at.is_(None)) | (APIKey.expires_at > datetime.utcnow())
                )
            )
        )
        api_keys = result.scalars().all()
        
        # Find matching key by comparing hashes
        for api_key in api_keys:
            if APIKeyManager.verify_key(secret_key, api_key.key_hash):
                # Check IP restrictions
                if api_key.allowed_ips and client_ip:
                    if client_ip not in api_key.allowed_ips:
                        return None
                
                # Check required scopes
                if required_scopes:
                    if not all(scope in api_key.scopes for scope in required_scopes):
                        return None
                
                # Check rate limiting
                if not await APIKeyManager.check_rate_limit(db, api_key):
                    return None
                
                # Update last used timestamp
                await db.execute(
                    update(APIKey)
                    .where(APIKey.id == api_key.id)
                    .values(last_used_at=datetime.utcnow())
                )
                
                return api_key
        
        return None
    
    @staticmethod
    async def check_rate_limit(db: AsyncSession, api_key: APIKey) -> bool:
        """
        Check if API key is within rate limits.
        
        Args:
            db: Database session
            api_key: The API key to check
            
        Returns:
            True if within limits, False if rate limited
        """
        if not api_key.rate_limit:
            return True
        
        # Determine time window based on rate limit period
        now = datetime.utcnow()
        if api_key.rate_limit_period == RateLimitType.requests_per_minute:
            window_start = now - timedelta(minutes=1)
        elif api_key.rate_limit_period == RateLimitType.requests_per_hour:
            window_start = now - timedelta(hours=1)
        elif api_key.rate_limit_period == RateLimitType.requests_per_day:
            window_start = now - timedelta(days=1)
        elif api_key.rate_limit_period == RateLimitType.requests_per_month:
            window_start = now - timedelta(days=30)
        else:
            return True
        
        # Count requests in the time window
        result = await db.execute(
            select(func.count(APIKeyUsage.id))
            .where(
                and_(
                    APIKeyUsage.api_key_id == api_key.id,
                    APIKeyUsage.timestamp >= window_start
                )
            )
        )
        request_count = result.scalar()
        
        return request_count < api_key.rate_limit
    
    @staticmethod
    async def log_api_usage(
        db: AsyncSession,
        api_key_id: UUID,
        method: str,
        endpoint: str,
        status_code: int,
        response_time_ms: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Log API key usage for analytics.
        
        Args:
            db: Database session
            api_key_id: The API key ID
            method: HTTP method
            endpoint: API endpoint
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            ip_address: Client IP address
            user_agent: Client user agent
            request_size_bytes: Request size in bytes
            response_size_bytes: Response size in bytes
            error_code: Error code if applicable
            error_message: Error message if applicable
        """
        usage_record = APIKeyUsage(
            api_key_id=api_key_id,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            error_code=error_code,
            error_message=error_message
        )
        
        db.add(usage_record)
        
        # Update API key usage counters
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Update total requests  
        await db.execute(
            update(APIKey)
            .where(APIKey.id == api_key_id)
            .values(
                total_requests=APIKey.total_requests + 1,
                last_request_reset=now
            )
        )
        
        # Reset daily counter if needed
        result = await db.execute(
            select(APIKey.last_request_reset).where(APIKey.id == api_key_id)
        )
        last_reset = result.scalar()
        
        if not last_reset or last_reset < today_start:
            # Reset daily counter
            await db.execute(
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(requests_today=1)
            )
        else:
            # Increment daily counter
            await db.execute(
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(requests_today=APIKey.requests_today + 1)
            )
    
    @staticmethod
    async def revoke_api_key(
        db: AsyncSession,
        api_key_id: UUID,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Revoke an API key.
        
        Args:
            db: Database session
            api_key_id: The API key ID to revoke
            user_id: Optional user ID for ownership verification
            
        Returns:
            True if revoked successfully, False otherwise
        """
        query = update(APIKey).where(APIKey.id == api_key_id)
        
        if user_id:
            query = query.where(APIKey.user_id == user_id)
        
        result = await db.execute(
            query.values(
                status=APIKeyStatus.revoked,
                updated_at=datetime.utcnow()
            )
        )
        
        return result.rowcount > 0
    
    @staticmethod
    async def rotate_api_key(
        db: AsyncSession,
        api_key_id: UUID,
        user_id: UUID,
        new_name: Optional[str] = None
    ) -> Optional[Tuple[APIKey, str]]:
        """
        Rotate an API key (create new, revoke old).
        
        Args:
            db: Database session
            api_key_id: The API key ID to rotate
            user_id: User ID for ownership verification
            new_name: Optional new name for the key
            
        Returns:
            Tuple of (new_api_key, secret_key) if successful, None otherwise
        """
        # Get the existing API key
        result = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.id == api_key_id,
                    APIKey.user_id == user_id
                )
            )
        )
        old_api_key = result.scalar_one_or_none()
        
        if not old_api_key:
            return None
        
        # Generate new key pair
        key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
        
        # Create new API key with same settings
        new_api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=new_name or f"{old_api_key.name} (Rotated)",
            description=old_api_key.description,
            user_id=user_id,
            scopes=old_api_key.scopes,
            allowed_ips=old_api_key.allowed_ips,
            allowed_domains=old_api_key.allowed_domains,
            rate_limit=old_api_key.rate_limit,
            rate_limit_period=old_api_key.rate_limit_period,
            expires_at=old_api_key.expires_at,
            extra_data=old_api_key.extra_data or {}
        )
        
        db.add(new_api_key)
        
        # Revoke old key
        await db.execute(
            update(APIKey)
            .where(APIKey.id == api_key_id)
            .values(
                status=APIKeyStatus.revoked,
                updated_at=datetime.utcnow()
            )
        )
        
        await db.commit()
        await db.refresh(new_api_key)
        
        return new_api_key, secret_key
    
    @staticmethod
    def has_scope(api_key: APIKey, required_scope: str) -> bool:
        """
        Check if API key has required scope.
        
        Args:
            api_key: The API key object
            required_scope: The required scope
            
        Returns:
            True if key has scope, False otherwise
        """
        if not api_key.scopes:
            return False
        
        # Admin scope grants all permissions
        if APIKeyScope.admin in api_key.scopes:
            return True
        
        # Check for specific scope
        return required_scope in api_key.scopes
    
    @staticmethod
    def get_scope_hierarchy() -> dict:
        """
        Get the scope hierarchy for permission checking.
        
        Returns:
            Dictionary mapping scopes to their permissions
        """
        return {
            APIKeyScope.read: [APIKeyScope.read],
            APIKeyScope.write: [APIKeyScope.read, APIKeyScope.write],
            APIKeyScope.admin: [
                APIKeyScope.read, 
                APIKeyScope.write, 
                APIKeyScope.admin,
                APIKeyScope.analytics,
                APIKeyScope.user_management,
                APIKeyScope.api_management
            ],
            APIKeyScope.analytics: [APIKeyScope.read, APIKeyScope.analytics],
            APIKeyScope.user_management: [APIKeyScope.read, APIKeyScope.user_management],
            APIKeyScope.api_management: [APIKeyScope.read, APIKeyScope.api_management]
        }


# Utility functions for scope checking
def require_api_key_scope(required_scope: str):
    """
    Decorator to require specific API key scope.
    
    Args:
        required_scope: The required scope
    """
    def decorator(func):
        func._required_api_scope = required_scope
        return func
    return decorator


def check_api_key_permissions(api_key: APIKey, required_scopes: List[str]) -> bool:
    """
    Check if API key has all required scopes.
    
    Args:
        api_key: The API key object
        required_scopes: List of required scopes
        
    Returns:
        True if key has all scopes, False otherwise
    """
    hierarchy = APIKeyManager.get_scope_hierarchy()
    user_permissions = set()
    
    # Build user's effective permissions
    for scope in api_key.scopes:
        if scope in hierarchy:
            user_permissions.update(hierarchy[scope])
    
    # Check if all required scopes are covered
    return all(scope in user_permissions for scope in required_scopes)