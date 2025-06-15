"""
Security utilities for authentication and authorization.
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


class PasswordSecurityError(SecurityError):
    """Exception raised for password validation errors."""
    pass


class TokenError(SecurityError):
    """Exception raised for token-related errors."""
    pass


def get_password_hash(password: str) -> str:
    """
    Generate a secure hash for a password.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def validate_password_strength(password: str) -> bool:
    """
    Validate password strength based on configured requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        True if password meets requirements
        
    Raises:
        PasswordSecurityError: If password doesn't meet requirements
    """
    errors = []
    
    # Check minimum length
    if len(password) < settings.password_min_length:
        errors.append(f"Password must be at least {settings.password_min_length} characters long")
    
    # Check for uppercase letters
    if settings.password_require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letters
    if settings.password_require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for numbers
    if settings.password_require_numbers and not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    
    # Check for special characters
    if settings.password_require_special and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        errors.append("Password must contain at least one special character")
    
    if errors:
        raise PasswordSecurityError("; ".join(errors))
    
    return True


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    # Add standard claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),  # Unique token ID for blacklisting
        "type": "access"
    })
    
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User ID to encode in the token
        
    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days)
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),
        "type": "refresh"
    }
    
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        TokenError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise TokenError(f"Invalid token: {str(e)}")


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify a JWT token and check its type.
    
    Args:
        token: JWT token string to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Decoded token payload
        
    Raises:
        TokenError: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)
    
    # Check token type
    if payload.get("type") != token_type:
        raise TokenError(f"Invalid token type. Expected {token_type}")
    
    # Check expiration (jose library handles this, but we can add custom logic)
    exp = payload.get("exp")
    if exp and datetime.utcnow().timestamp() > exp:
        raise TokenError("Token has expired")
    
    return payload


def extract_token_jti(token: str) -> str:
    """
    Extract the JTI (JWT ID) from a token for blacklisting.
    
    Args:
        token: JWT token string
        
    Returns:
        Token JTI string
        
    Raises:
        TokenError: If token is invalid or has no JTI
    """
    payload = decode_token(token)
    jti = payload.get("jti")
    
    if not jti:
        raise TokenError("Token has no JTI claim")
    
    return jti


def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create both access and refresh tokens for a user.
    
    Args:
        user_data: User data to encode in tokens
        
    Returns:
        Dictionary containing both tokens and metadata
    """
    # Create access token
    access_token = create_access_token(user_data)
    
    # Create refresh token (only needs user ID)
    refresh_token = create_refresh_token(user_data["sub"])
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_minutes * 60,  # In seconds
        "refresh_expires_in": settings.jwt_refresh_expire_days * 24 * 60 * 60  # In seconds
    }


def generate_secure_random_string(length: int = 32) -> str:
    """
    Generate a cryptographically secure random string.
    
    Args:
        length: Length of the string to generate
        
    Returns:
        Random string
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))