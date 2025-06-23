"""
API Key models for managing programmatic access to the developer portal.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import DateTime, func, Enum as SQLEnum, ARRAY, Text
from sqlalchemy.dialects.postgresql import JSONB


class APIKeyStatus(str, Enum):
    """API Key status enumeration."""
    active = "active"
    inactive = "inactive"
    revoked = "revoked"


class APIKeyScope(str, Enum):
    """API Key permission scopes."""
    read = "read"                    # Read-only access
    write = "write"                  # Read + Create/Update
    admin = "admin"                  # Full access including delete
    analytics = "analytics"          # Access to usage analytics
    user_management = "user_management"  # User CRUD operations
    api_management = "api_management"    # API key CRUD operations
    payment_read = "payment:read"    # Read payment data
    payment_write = "payment:write"  # Process payments and refunds
    payment_admin = "payment:admin"  # Full payment administration


class RateLimitType(str, Enum):
    """Rate limiting types."""
    requests_per_minute = "requests_per_minute"
    requests_per_hour = "requests_per_hour"
    requests_per_day = "requests_per_day"
    requests_per_month = "requests_per_month"


# Database Models
class APIKey(SQLModel, table=True):
    """
    API Key model for programmatic access.
    """
    __tablename__ = "api_keys"
    
    # Primary Fields
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    key_id: str = Field(unique=True, index=True)  # Public identifier (ak_...)
    key_hash: str = Field()  # Hashed secret key
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    
    # Ownership
    user_id: UUID = Field(foreign_key="users.id", index=True)
    user: Optional["User"] = Relationship(back_populates="api_keys")
    
    # Status and Lifecycle  
    status: APIKeyStatus = Field(
        default=APIKeyStatus.active,
        sa_column=Column(SQLEnum(APIKeyStatus, name="api_key_status"))
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, onupdate=func.now()))
    last_used_at: Optional[datetime] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    
    # Permissions and Scopes
    scopes: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(Text)))
    allowed_ips: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    allowed_domains: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    
    # Rate Limiting
    rate_limit: Optional[int] = Field(default=1000)  # Requests per period
    rate_limit_period: RateLimitType = Field(default=RateLimitType.requests_per_hour)
    
    # Usage Tracking
    total_requests: int = Field(default=0)
    requests_today: int = Field(default=0)
    last_request_reset: Optional[datetime] = Field(default=None)
    
    # Metadata
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSONB))


class APIKeyUsage(SQLModel, table=True):
    """
    API Key usage tracking for analytics.
    """
    __tablename__ = "api_key_usage"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    api_key_id: UUID = Field(foreign_key="api_keys.id", index=True)
    
    # Request Details
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    method: str = Field(max_length=10)
    endpoint: str = Field(max_length=255)
    status_code: int = Field()
    response_time_ms: Optional[float] = Field(default=None)
    
    # Client Information
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    referer: Optional[str] = Field(default=None, max_length=500)
    
    # Request/Response Sizes
    request_size_bytes: Optional[int] = Field(default=None)
    response_size_bytes: Optional[int] = Field(default=None)
    
    # Error Information
    error_code: Optional[str] = Field(default=None, max_length=50)
    error_message: Optional[str] = Field(default=None, max_length=500)


# Pydantic Models for API
class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    scopes: List[APIKeyScope] = Field(default_factory=lambda: [APIKeyScope.read])
    expires_at: Optional[datetime] = Field(default=None)
    allowed_ips: Optional[List[str]] = Field(default=None)
    allowed_domains: Optional[List[str]] = Field(default=None)
    rate_limit: Optional[int] = Field(default=1000, ge=1, le=100000)
    rate_limit_period: RateLimitType = Field(default=RateLimitType.requests_per_hour)
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('expires_at')
    def validate_expiration(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Expiration date must be in the future')
        return v
    
    @validator('allowed_ips')
    def validate_ips(cls, v):
        if v:
            # Basic IP validation - could be enhanced
            for ip in v:
                if not ip.replace('.', '').replace(':', '').replace('/', '').isalnum():
                    raise ValueError(f'Invalid IP address format: {ip}')
        return v


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    scopes: Optional[List[APIKeyScope]] = Field(default=None)
    status: Optional[APIKeyStatus] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    allowed_ips: Optional[List[str]] = Field(default=None)
    allowed_domains: Optional[List[str]] = Field(default=None)
    rate_limit: Optional[int] = Field(default=None, ge=1, le=100000)
    rate_limit_period: Optional[RateLimitType] = Field(default=None)
    extra_data: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator('expires_at')
    def validate_expiration(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Expiration date must be in the future')
        return v


class APIKeyResponse(BaseModel):
    """Schema for API key responses (without sensitive data)."""
    id: UUID
    key_id: str
    name: str
    description: Optional[str]
    status: APIKeyStatus
    scopes: List[str]
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    allowed_ips: Optional[List[str]]
    allowed_domains: Optional[List[str]]
    rate_limit: Optional[int]
    rate_limit_period: RateLimitType
    total_requests: int
    requests_today: int
    extra_data: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Schema for API key creation response (includes the secret key)."""
    api_key: APIKeyResponse
    secret_key: str = Field(description="The actual API key - store this securely, it won't be shown again")
    
    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Schema for paginated API key list."""
    api_keys: List[APIKeyResponse]
    total: int
    page: int
    size: int
    pages: int


class APIKeyUsageResponse(BaseModel):
    """Schema for API key usage statistics."""
    api_key_id: UUID
    total_requests: int
    requests_today: int
    requests_this_week: int
    requests_this_month: int
    average_response_time_ms: Optional[float]
    error_rate_percent: Optional[float]
    top_endpoints: List[Dict[str, Any]]
    usage_by_day: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class APIKeyValidation(BaseModel):
    """Schema for API key validation results."""
    valid: bool
    api_key_id: Optional[str] = None
    user_id: Optional[UUID] = None
    scopes: Optional[List[str]] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None
    error: Optional[str] = None


# Request/Response Models for specific operations
class APIKeyRevoke(BaseModel):
    """Schema for revoking an API key."""
    reason: Optional[str] = Field(default=None, max_length=200)


class APIKeyRotate(BaseModel):
    """Schema for rotating an API key."""
    new_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    copy_settings: bool = Field(default=True, description="Copy scopes and settings from old key")


class APIKeyRotateResponse(BaseModel):
    """Schema for API key rotation response."""
    old_key_id: str
    new_api_key: APIKeyResponse
    new_secret_key: str = Field(description="The new API key - store this securely")
    
    class Config:
        from_attributes = True


class BulkAPIKeyOperation(BaseModel):
    """Schema for bulk operations on API keys."""
    api_key_ids: List[UUID] = Field(min_items=1, max_items=50)
    operation: str = Field(regex="^(revoke|suspend|activate)$")
    reason: Optional[str] = Field(default=None, max_length=200)


class BulkAPIKeyOperationResponse(BaseModel):
    """Schema for bulk operation results."""
    successful: List[UUID]
    failed: List[Dict[str, Any]]  # {"api_key_id": UUID, "error": str}
    total_processed: int