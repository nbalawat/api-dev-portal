"""
Authentication router for login, logout, and token management.
"""
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..core.security import (
    verify_password, 
    create_token_pair, 
    verify_token, 
    extract_token_jti,
    TokenError
)
from ..dependencies.database import get_database
from ..dependencies.auth import get_current_active_user, oauth2_scheme
from ..models.user import User, UserLogin, UserResponse
from ..models.token import (
    TokenResponse, 
    TokenRefresh, 
    TokenRefreshResponse,
    TokenBlacklist,
    TokenBlacklistCreate,
    LogoutRequest,
    LogoutResponse
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_database)
) -> TokenResponse:
    """
    User login with username/email and password.
    
    Returns JWT access and refresh tokens for authenticated users.
    """
    # Get user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == form_data.username) | 
            (User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Update last login time
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login=datetime.utcnow())
    )
    await db.commit()
    
    # Create token pair
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "username": user.username
    }
    
    tokens = create_token_pair(token_data)
    
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_database)
) -> TokenRefreshResponse:
    """
    Refresh access token using refresh token.
    
    Returns a new access token if refresh token is valid.
    """
    try:
        # Verify refresh token
        payload = verify_token(token_data.refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token is blacklisted
        token_jti = payload.get("jti")
        if token_jti:
            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.token_jti == token_jti)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has been revoked"
                )
        
        # Get user data
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        from ..core.security import create_access_token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "username": user.username
        }
        
        access_token = create_access_token(token_data)
        
        return TokenRefreshResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=30 * 60  # 30 minutes in seconds
        )
        
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    logout_data: LogoutRequest = LogoutRequest(),
    current_user: User = Depends(get_current_active_user),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_database)
) -> LogoutResponse:
    """
    Logout user and blacklist current token(s).
    
    Optionally revoke all tokens for the user.
    """
    tokens_revoked = 0
    
    try:
        # Extract current token JTI
        current_jti = extract_token_jti(token)
        current_payload = verify_token(token, token_type="access")
        
        # Blacklist current access token
        blacklist_entry = TokenBlacklist(
            token_jti=current_jti,
            user_id=current_user.id,
            token_type="access",
            expires_at=datetime.fromtimestamp(current_payload.get("exp")),
            reason="logout"
        )
        db.add(blacklist_entry)
        tokens_revoked += 1
        
        # If revoke_all is True, blacklist all active tokens for the user
        if logout_data.revoke_all:
            # This would require tracking all active tokens
            # For now, we'll just blacklist the current token
            # In a production system, you might maintain a table of active tokens
            pass
        
        await db.commit()
        
        return LogoutResponse(
            message="Successfully logged out",
            tokens_revoked=tokens_revoked
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current user's profile information.
    
    Returns the authenticated user's profile data.
    """
    return UserResponse.from_orm(current_user)


@router.get("/verify")
async def verify_token_endpoint(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Verify the current token and return user information.
    
    Useful for frontend applications to check token validity.
    """
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified
    }


@router.get("/status")
async def auth_status() -> Dict[str, Any]:
    """
    Get authentication system status and configuration.
    
    Returns information about the authentication system.
    """
    from ..core.config import settings
    
    return {
        "authentication": "enabled",
        "token_type": "JWT",
        "algorithm": settings.jwt_algorithm,
        "access_token_expire_minutes": settings.jwt_expire_minutes,
        "refresh_token_expire_days": settings.jwt_refresh_expire_days,
        "password_requirements": {
            "min_length": settings.password_min_length,
            "require_uppercase": settings.password_require_uppercase,
            "require_lowercase": settings.password_require_lowercase,
            "require_numbers": settings.password_require_numbers,
            "require_special": settings.password_require_special
        },
        "supported_roles": ["admin", "developer", "viewer"]
    }