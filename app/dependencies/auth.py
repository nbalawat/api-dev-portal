"""
Authentication dependencies for FastAPI.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.security import verify_token, TokenError
from ..dependencies.database import get_database
from ..models.user import User, UserRole


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scheme_name="JWT"
)


class AuthenticationError(HTTPException):
    """Custom authentication error."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error."""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_database)
) -> User:
    """
    Get current user from JWT token.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    try:
        # Verify and decode token
        payload = verify_token(token, token_type="access")
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise AuthenticationError("User not found")
        
        return user
        
    except TokenError as e:
        raise AuthenticationError(str(e))
    except Exception as e:
        raise AuthenticationError("Token validation failed")


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Active user object
        
    Raises:
        AuthenticationError: If user is inactive
    """
    if not current_user.is_active:
        raise AuthenticationError("Inactive user")
    
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user.
    
    Args:
        current_user: Current active user
        
    Returns:
        Verified user object
        
    Raises:
        AuthenticationError: If user is not verified
    """
    if not current_user.is_verified:
        raise AuthenticationError("User not verified")
    
    return current_user


def require_role(required_role: UserRole):
    """
    Create a dependency that requires a specific role or higher.
    
    Args:
        required_role: Minimum required role
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # Define role hierarchy (higher number = more permissions)
        role_hierarchy = {
            UserRole.viewer: 1,
            UserRole.developer: 2,
            UserRole.admin: 3
        }
        
        user_role_level = role_hierarchy.get(current_user.role, 0)
        required_role_level = role_hierarchy.get(required_role, 999)
        
        if user_role_level < required_role_level:
            raise AuthorizationError(
                f"Role '{required_role}' or higher required"
            )
        
        return current_user
    
    return role_checker


# Pre-defined role dependencies
require_admin = require_role(UserRole.admin)
require_developer = require_role(UserRole.developer)
require_viewer = require_role(UserRole.viewer)


async def get_admin_user(
    current_user: User = Depends(require_admin)
) -> User:
    """Get current user with admin role."""
    return current_user


async def get_developer_user(
    current_user: User = Depends(require_developer)
) -> User:
    """Get current user with developer role or higher."""
    return current_user


async def get_viewer_user(
    current_user: User = Depends(require_viewer)
) -> User:
    """Get current user with viewer role or higher."""
    return current_user


# Optional: Token blacklist checking (will be implemented later)
async def check_token_blacklist(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_database)
) -> str:
    """
    Check if token is blacklisted.
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        Token if not blacklisted
        
    Raises:
        AuthenticationError: If token is blacklisted
    """
    # TODO: Implement blacklist checking when TokenBlacklist model is ready
    # from ..models.token import TokenBlacklist
    # from ..core.security import extract_token_jti
    
    # try:
    #     jti = extract_token_jti(token)
    #     result = await db.execute(
    #         select(TokenBlacklist).where(TokenBlacklist.token_jti == jti)
    #     )
    #     blacklisted_token = result.scalar_one_or_none()
    #     
    #     if blacklisted_token:
    #         raise AuthenticationError("Token has been revoked")
    # except Exception:
    #     pass  # If we can't check, allow the token (graceful degradation)
    
    return token