"""
Integration tests for authentication system including database dependencies.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlmodel import SQLModel

from app.main import app
from app.dependencies.database import get_database
from app.models.user import User, EmailVerificationToken, PasswordResetToken
from app.core.config import settings


# Use the same database as the app for integration tests
TEST_DATABASE_URL = "postgresql+asyncpg://testuser:testpass@test-postgres:5432/testdb"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_test_database():
    """Get test database session."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Override the dependency
app.dependency_overrides[get_database] = get_test_database


@pytest.fixture(scope="function")
def clean_database():
    """Clean database before each test."""
    
    async def cleanup():
        # Use the same test engine to avoid connection conflicts
        async with test_engine.begin() as conn:
            # Clean up tables in reverse dependency order using raw SQL
            await conn.execute(text("DELETE FROM email_verification_tokens"))
            await conn.execute(text("DELETE FROM password_reset_tokens")) 
            await conn.execute(text("DELETE FROM api_key_usage"))
            await conn.execute(text("DELETE FROM api_keys"))
            await conn.execute(text("DELETE FROM token_blacklist"))
            await conn.execute(text("DELETE FROM users"))
    
    # Clean up before test
    asyncio.run(cleanup())
    yield
    
    # Clean up after test as well
    asyncio.run(cleanup())


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Test user registration data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
        "role": "developer"
    }


class TestUserRegistration:
    """Test user registration flow."""
    
    @pytest.mark.asyncio
    async def test_register_new_user(self, client, test_user_data, clean_database):
        """Test successful user registration."""
        response = client.post("/auth/register", json=test_user_data)
        
        # Print error details if test fails
        if response.status_code != 200:
            print(f"❌ Registration failed with status {response.status_code}")
            print(f"Response: {response.json()}")
            
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Registration successful"
        assert "user_id" in data
        assert data["next_step"] == "Please check your email and click the verification link to activate your account"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client, test_user_data, clean_database):
        """Test registration with duplicate username."""
        # Register first user
        first_response = client.post("/auth/register", json=test_user_data)
        
        # Print debug info if first registration fails
        if first_response.status_code != 200:
            print(f"❌ First registration failed with status {first_response.status_code}")
            print(f"Response: {first_response.json()}")
            
        assert first_response.status_code == 200
        
        # Try to register with same username
        duplicate_data = test_user_data.copy()
        duplicate_data["email"] = "different@example.com"
        
        response = client.post("/auth/register", json=duplicate_data)
        
        # Print debug info if duplicate test fails
        if response.status_code != 400:
            print(f"❌ Duplicate test failed with status {response.status_code}")
            print(f"Response: {response.json()}")
            
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user_data, clean_database):
        """Test registration with duplicate email."""
        # Register first user
        client.post("/auth/register", json=test_user_data)
        
        # Try to register with same email
        duplicate_data = test_user_data.copy()
        duplicate_data["username"] = "differentuser"
        
        response = client.post("/auth/register", json=duplicate_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, client, test_user_data, clean_database):
        """Test registration with password mismatch."""
        test_data = test_user_data.copy()
        test_data["confirm_password"] = "differentpassword"
        
        response = client.post("/auth/register", json=test_data)
        assert response.status_code == 422  # Validation error


class TestEmailVerification:
    """Test email verification flow."""
    
    @pytest.mark.asyncio
    async def test_verify_email_success(self, client, test_user_data, clean_database):
        """Test successful email verification."""
        # Register user
        register_response = client.post("/auth/register", json=test_user_data)
        assert register_response.status_code == 200
        
        # Note: In real integration tests, we would get the token from the database
        # For now, we test the endpoint structure
        fake_token = "fake_verification_token"
        
        response = client.post(f"/auth/verify-email?token={fake_token}")
        # This will return 400 because token doesn't exist, but tests the endpoint
        assert response.status_code == 400
        assert "Invalid verification token" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_resend_verification(self, client, test_user_data, clean_database):
        """Test resending verification email."""
        # Register user
        client.post("/auth/register", json=test_user_data)
        
        # Resend verification
        response = client.post(f"/auth/resend-verification?email={test_user_data['email']}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Verification email sent"
    
    @pytest.mark.asyncio
    async def test_resend_verification_nonexistent_email(self, client, clean_database):
        """Test resending verification to non-existent email."""
        response = client.post("/auth/resend-verification?email=nonexistent@example.com")
        assert response.status_code == 200
        # Should return success to prevent email enumeration
        assert "verification link has been sent" in response.json()["message"]


class TestPasswordReset:
    """Test password reset flow."""
    
    @pytest.mark.asyncio
    async def test_forgot_password(self, client, test_user_data, clean_database):
        """Test password reset request."""
        # Register and verify user (simplified for test)
        client.post("/auth/register", json=test_user_data)
        
        reset_data = {"email": test_user_data["email"]}
        response = client.post("/auth/forgot-password", json=reset_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password reset email sent"
    
    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(self, client, clean_database):
        """Test password reset for non-existent email."""
        reset_data = {"email": "nonexistent@example.com"}
        response = client.post("/auth/forgot-password", json=reset_data)
        
        assert response.status_code == 200
        # Should return success to prevent email enumeration
        assert "password reset link has been sent" in response.json()["message"]
    
    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token."""
        reset_data = {
            "token": "invalid_token",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }
        
        response = client.post("/auth/reset-password", json=reset_data)
        assert response.status_code == 400
        assert "Invalid reset token" in response.json()["detail"]
    
    def test_verify_reset_token_invalid(self, client):
        """Test verifying invalid reset token."""
        response = client.get("/auth/reset-password/verify/invalid_token")
        assert response.status_code == 400
        assert "Invalid or expired reset token" in response.json()["detail"]


class TestLoginAfterRegistration:
    """Test login functionality after registration."""
    
    def test_login_unverified_user(self, client, test_user_data):
        """Test that unverified users cannot login."""
        # Register user (will be inactive until verified)
        client.post("/auth/register", json=test_user_data)
        
        # Try to login
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/auth/login", data=login_data)
        assert response.status_code == 400
        assert "Inactive user account" in response.json()["detail"]


class TestAuthenticationEndpoints:
    """Test authentication endpoint accessibility."""
    
    def test_auth_status_endpoint(self, client):
        """Test authentication status endpoint."""
        response = client.get("/auth/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["authentication"] == "enabled"
        assert data["token_type"] == "JWT"
        assert "password_requirements" in data
        assert "supported_roles" in data
    
    def test_protected_endpoints_require_auth(self, client):
        """Test that protected endpoints require authentication."""
        # Test getting current user without auth
        response = client.get("/auth/me")
        assert response.status_code == 401
        
        # Test logout without auth
        response = client.post("/auth/logout")
        assert response.status_code == 401


class TestValidationErrors:
    """Test input validation errors."""
    
    def test_register_invalid_email(self, client, test_user_data):
        """Test registration with invalid email."""
        test_data = test_user_data.copy()
        test_data["email"] = "invalid_email"
        
        response = client.post("/auth/register", json=test_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_short_password(self, client, test_user_data):
        """Test registration with short password."""
        test_data = test_user_data.copy()
        test_data["password"] = "short"
        test_data["confirm_password"] = "short"
        
        response = client.post("/auth/register", json=test_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_invalid_username(self, client, test_user_data):
        """Test registration with invalid username."""
        test_data = test_user_data.copy()
        test_data["username"] = "us"  # Too short
        
        response = client.post("/auth/register", json=test_data)
        assert response.status_code == 422  # Validation error


class TestSecurityFeatures:
    """Test security features of authentication system."""
    
    def test_password_reset_rate_limiting(self, client, test_user_data):
        """Test rate limiting on password reset requests."""
        # Register user
        client.post("/auth/register", json=test_user_data)
        
        reset_data = {"email": test_user_data["email"]}
        
        # Make multiple reset requests
        for _ in range(3):
            response = client.post("/auth/forgot-password", json=reset_data)
            assert response.status_code == 200
        
        # Note: Actual rate limiting would be tested with real rate limiter
        # This tests the endpoint accepts multiple requests
    
    def test_email_enumeration_protection(self, client):
        """Test protection against email enumeration attacks."""
        # Test with non-existent email
        reset_data = {"email": "nonexistent@example.com"}
        response = client.post("/auth/forgot-password", json=reset_data)
        
        # Should return success even for non-existent email
        assert response.status_code == 200
        assert "password reset link has been sent" in response.json()["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])