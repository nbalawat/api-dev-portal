"""
User models and schemas for authentication and user management.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum
import secrets

from sqlmodel import SQLModel, Field, Column, String, Relationship
from sqlalchemy import DateTime, func
from pydantic import EmailStr, validator


class UserRole(str, Enum):
    """User role enumeration with hierarchy."""
    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class UserStatus(str, Enum):
    """User status enumeration."""
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


# SQLModel for database table
class User(SQLModel, table=True):
    """User database model."""
    __tablename__ = "users"
    
    # Primary key
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        description="Unique user identifier"
    )
    
    # Authentication fields
    username: str = Field(
        index=True,
        unique=True,
        min_length=3,
        max_length=50,
        regex=r"^[a-zA-Z0-9_-]+$",
        description="Unique username (alphanumeric, underscore, dash only)"
    )
    email: str = Field(
        index=True,
        unique=True,
        max_length=255,
        description="User email address"
    )
    hashed_password: str = Field(
        max_length=255,
        description="Bcrypt hashed password"
    )
    
    # Profile fields
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User's full name"
    )
    
    # Authorization fields
    role: UserRole = Field(
        default=UserRole.developer,
        description="User role for access control"
    )
    
    # Status fields
    is_active: bool = Field(
        default=True,
        description="Whether user can authenticate"
    )
    is_verified: bool = Field(
        default=False,
        description="Whether user email is verified"
    )
    is_superuser: bool = Field(
        default=False,
        description="Whether user has superuser privileges"
    )
    
    # Relationships
    api_keys: List["APIKey"] = Relationship(back_populates="user")
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Account creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="Last update timestamp"
    )
    last_login: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Last login timestamp"
    )
    
    # Optional fields
    avatar_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL to user avatar image"
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User biography/description"
    )
    timezone: Optional[str] = Field(
        default="UTC",
        max_length=50,
        description="User's timezone"
    )
    
    class Config:
        arbitrary_types_allowed = True


# Pydantic schemas for API requests/responses

class UserBase(SQLModel):
    """Base user schema with common fields."""
    username: str = Field(
        min_length=3,
        max_length=50,
        regex=r"^[a-zA-Z0-9_-]+$",
        description="Unique username"
    )
    email: EmailStr = Field(description="User email address")
    full_name: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    timezone: Optional[str] = Field(default="UTC", max_length=50)
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not v:
            raise ValueError('Username cannot be empty')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('Username must be at most 50 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and dashes')
        return v.lower()


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(
        min_length=8,
        max_length=128,
        description="User password (will be hashed)"
    )
    role: UserRole = Field(default=UserRole.developer, description="User role")
    is_active: bool = Field(default=True, description="User active status")
    
    @validator('password')
    def validate_password(cls, v):
        """Basic password validation."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password must be at most 128 characters long')
        return v


class UserUpdate(SQLModel):
    """Schema for user updates."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    timezone: Optional[str] = Field(default=None, max_length=50)
    avatar_url: Optional[str] = Field(default=None, max_length=500)


class UserUpdateAdmin(UserUpdate):
    """Schema for admin user updates (includes role and status)."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user responses (public data only)."""
    id: UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserResponseAdmin(UserResponse):
    """Schema for admin user responses (includes sensitive fields)."""
    is_superuser: bool
    
    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    """Schema for user profile (current user viewing their own data)."""
    pass


class UserLogin(SQLModel):
    """Schema for user login."""
    username: str = Field(description="Username or email")
    password: str = Field(description="User password")


class UserRegister(UserCreate):
    """Schema for user registration."""
    confirm_password: str = Field(description="Password confirmation")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordChange(SQLModel):
    """Schema for password changes."""
    current_password: str = Field(description="Current password")
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password"
    )
    confirm_password: str = Field(description="New password confirmation")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordReset(SQLModel):
    """Schema for password reset."""
    email: EmailStr = Field(description="User email address")


class PasswordResetConfirm(SQLModel):
    """Schema for password reset confirmation."""
    token: str = Field(description="Password reset token")
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password"
    )
    confirm_password: str = Field(description="New password confirmation")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# User list response schemas
class UserListResponse(SQLModel):
    """Schema for paginated user lists."""
    users: list[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class UserListResponseAdmin(SQLModel):
    """Schema for admin paginated user lists."""
    users: list[UserResponseAdmin]
    total: int
    page: int
    size: int
    pages: int


class EmailVerificationToken(SQLModel, table=True):
    """Email verification token model."""
    __tablename__ = "email_verification_tokens"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    token: str = Field(unique=True, index=True)
    expires_at: datetime = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = Field(default=None)
    
    @classmethod
    def create_token(cls, user_id: UUID, hours: int = 24) -> "EmailVerificationToken":
        """Create a new verification token."""
        return cls(
            user_id=user_id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(hours=hours)
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None
    
    def mark_used(self) -> None:
        """Mark token as used."""
        self.used_at = datetime.utcnow()


class PasswordResetToken(SQLModel, table=True):
    """Password reset token model."""
    __tablename__ = "password_reset_tokens"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    token: str = Field(unique=True, index=True)
    expires_at: datetime = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = Field(default=None)
    
    @classmethod
    def create_token(cls, user_id: UUID, hours: int = 1) -> "PasswordResetToken":
        """Create a new password reset token."""
        return cls(
            user_id=user_id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(hours=hours)
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None
    
    def mark_used(self) -> None:
        """Mark token as used."""
        self.used_at = datetime.utcnow()