"""
Token models and schemas for JWT token management.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime, func
from pydantic import validator


# SQLModel for token blacklist table
class TokenBlacklist(SQLModel, table=True):
    """Token blacklist database model for logout functionality."""
    __tablename__ = "token_blacklist"
    
    # Primary key
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        description="Unique blacklist entry identifier"
    )
    
    # Token identification
    token_jti: str = Field(
        index=True,
        unique=True,
        max_length=255,
        description="JWT Token ID (JTI) claim"
    )
    
    # User reference
    user_id: UUID = Field(
        foreign_key="users.id",
        index=True,
        description="User who owns the token"
    )
    
    # Token metadata
    token_type: str = Field(
        max_length=20,
        default="access",
        description="Type of token (access, refresh)"
    )
    
    # Expiration tracking
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="When the token expires"
    )
    
    # Audit fields
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="When token was blacklisted"
    )
    
    # Optional reason for blacklisting
    reason: Optional[str] = Field(
        default="logout",
        max_length=100,
        description="Reason for blacklisting (logout, revoked, etc.)"
    )
    
    class Config:
        arbitrary_types_allowed = True


# Pydantic schemas for API requests/responses

class TokenResponse(SQLModel):
    """Schema for token response."""
    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Access token expiry in seconds")
    refresh_expires_in: int = Field(description="Refresh token expiry in seconds")


class TokenRefresh(SQLModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(description="Refresh token")


class TokenRefreshResponse(SQLModel):
    """Schema for token refresh response."""
    access_token: str = Field(description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Access token expiry in seconds")


class TokenBlacklistCreate(SQLModel):
    """Schema for creating token blacklist entry."""
    token_jti: str = Field(description="JWT Token ID")
    user_id: UUID = Field(description="User ID")
    token_type: str = Field(default="access", description="Token type")
    expires_at: datetime = Field(description="Token expiration")
    reason: Optional[str] = Field(default="logout", description="Blacklist reason")


class TokenBlacklistResponse(SQLModel):
    """Schema for token blacklist response."""
    id: UUID
    token_jti: str
    user_id: UUID
    token_type: str
    expires_at: datetime
    created_at: datetime
    reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class TokenPayload(SQLModel):
    """Schema for JWT token payload."""
    sub: str = Field(description="Subject (user ID)")
    email: Optional[str] = Field(default=None, description="User email")
    role: Optional[str] = Field(default=None, description="User role")
    exp: int = Field(description="Expiration timestamp")
    iat: int = Field(description="Issued at timestamp")
    jti: str = Field(description="JWT ID")
    type: str = Field(description="Token type (access, refresh)")
    
    @validator('sub')
    def validate_subject(cls, v):
        """Validate subject is not empty."""
        if not v:
            raise ValueError('Subject cannot be empty')
        return v
    
    @validator('exp')
    def validate_expiration(cls, v):
        """Validate expiration is in the future."""
        if v <= datetime.utcnow().timestamp():
            raise ValueError('Token expiration must be in the future')
        return v


class TokenVerification(SQLModel):
    """Schema for token verification response."""
    valid: bool = Field(description="Whether token is valid")
    user_id: Optional[UUID] = Field(default=None, description="User ID if valid")
    role: Optional[str] = Field(default=None, description="User role if valid")
    expires_at: Optional[datetime] = Field(default=None, description="Token expiration")
    error: Optional[str] = Field(default=None, description="Error message if invalid")


class LogoutRequest(SQLModel):
    """Schema for logout request."""
    revoke_all: bool = Field(
        default=False,
        description="Whether to revoke all tokens for the user"
    )


class LogoutResponse(SQLModel):
    """Schema for logout response."""
    message: str = Field(description="Logout confirmation message")
    tokens_revoked: int = Field(description="Number of tokens revoked")


# Session management schemas
class UserSession(SQLModel):
    """Schema for user session information."""
    user_id: UUID = Field(description="User ID")
    username: str = Field(description="Username")
    email: str = Field(description="User email")
    role: str = Field(description="User role")
    is_active: bool = Field(description="User active status")
    is_verified: bool = Field(description="User verified status")
    last_login: Optional[datetime] = Field(default=None, description="Last login time")
    session_expires: datetime = Field(description="When session expires")


class ActiveSession(SQLModel):
    """Schema for active session display."""
    token_jti: str = Field(description="Session token ID")
    created_at: datetime = Field(description="Session start time")
    expires_at: datetime = Field(description="Session expiry time")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity")
    ip_address: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")
    is_current: bool = Field(description="Whether this is the current session")


class ActiveSessionsList(SQLModel):
    """Schema for list of active sessions."""
    sessions: list[ActiveSession]
    total: int = Field(description="Total number of active sessions")
    current_session_jti: str = Field(description="Current session token ID")