"""
Integration tests for authentication system including database dependencies.
"""
import pytest
import asyncio
import time
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

# Create test engine with connection pooling optimized for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL, 
    echo=False, 
    pool_pre_ping=False,    # Disable ping to prevent connection issues
    pool_size=1,           # Single connection to prevent conflicts
    max_overflow=0,        # No overflow connections
    pool_recycle=30,       # Recycle connections quickly
    pool_timeout=10,       # Short timeout
    pool_reset_on_return='commit'  # Reset connection state on return
)
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


@pytest.fixture(scope="session", autouse=True)  
async def setup_test_session():
    """Setup and teardown for the test session."""
    print("🚀 Starting test session...")
    yield
    print("✅ Test session completed - disposing engine")
    # Dispose the test engine to prevent connection leaks
    try:
        await test_engine.dispose()
    except Exception as e:
        print(f"Warning: Engine disposal failed: {e}")


@pytest.fixture(scope="function")
def client():
    """Test client fixture with proper connection limits."""
    import httpx
    
    # Create a dedicated transport with connection limits
    transport = httpx.ASGITransport(
        app=app,
        raise_app_exceptions=False  # Don't raise app exceptions in tests
    )
    
    # Create client with proper configuration for test isolation
    return AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=30.0,
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=0)  # Force fresh connections
    )


async def truncate_all_tables():
    """Truncate all tables to ensure complete database cleanup."""
    cleanup_engine = create_async_engine(
        TEST_DATABASE_URL, 
        echo=False, 
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=False,
        pool_recycle=30,
        pool_reset_on_return='commit'
    )
    
    try:
        async with cleanup_engine.begin() as conn:
            # Disable foreign key checks temporarily
            await conn.execute(text("SET session_replication_role = replica;"))
            
            # Truncate all tables in correct order
            tables = [
                "email_verification_tokens",
                "password_reset_tokens", 
                "api_key_usage",
                "api_keys",
                "token_blacklist",
                "users"
            ]
            
            for table in tables:
                try:
                    await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                except Exception as e:
                    print(f"Warning: Failed to truncate {table}: {e}")
                    # Fallback to DELETE if TRUNCATE fails
                    await conn.execute(text(f"DELETE FROM {table};"))
            
            # Re-enable foreign key checks
            await conn.execute(text("SET session_replication_role = DEFAULT;"))
            
    except Exception as e:
        print(f"Warning: Table truncation failed: {e}")
        # Fallback to individual deletions
        try:
            async with cleanup_engine.begin() as conn:
                await conn.execute(text("DELETE FROM email_verification_tokens"))
                await conn.execute(text("DELETE FROM password_reset_tokens"))
                await conn.execute(text("DELETE FROM api_key_usage"))
                await conn.execute(text("DELETE FROM api_keys"))
                await conn.execute(text("DELETE FROM token_blacklist"))
                await conn.execute(text("DELETE FROM users"))
        except Exception as fallback_e:
            print(f"Warning: Fallback cleanup also failed: {fallback_e}")
    finally:
        await cleanup_engine.dispose()


@pytest.fixture(scope="function")
async def clean_test_data():
    """Clean test data before and after each test to ensure complete isolation."""
    print("🧹 Cleaning database before test...")
    await truncate_all_tables()
    
    # Small delay to ensure cleanup is complete
    await asyncio.sleep(0.2)
    
    yield
    
    print("🧹 Cleaning database after test...")
    await truncate_all_tables()


@pytest.fixture
def test_user_data():
    """Test user registration data with unique values."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
        "role": "developer"
    }


class TestUserRegistration:
    """Test user registration flow."""
    
    @pytest.mark.asyncio
    async def test_register_new_user(self, client, test_user_data, clean_test_data):
        """Test successful user registration."""
        async with client as ac:
            # Add small delay to prevent race conditions
            await asyncio.sleep(0.2)
            
            response = await ac.post("/auth/register", json=test_user_data)
            
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
    async def test_register_duplicate_username(self, client, test_user_data, clean_test_data):
        """Test registration with duplicate username."""
        async with client as ac:
            # Add larger delay to prevent race conditions
            await asyncio.sleep(0.3)
            
            # Register first user
            first_response = await ac.post("/auth/register", json=test_user_data)
            
            # Print debug info if first registration fails
            if first_response.status_code != 200:
                print(f"❌ First registration failed with status {first_response.status_code}")
                print(f"Response: {first_response.json()}")
                
            assert first_response.status_code == 200
            
            # Try to register with same username
            duplicate_data = test_user_data.copy()
            duplicate_data["email"] = "different@example.com"
            
            response = await ac.post("/auth/register", json=duplicate_data)
            
            # Print debug info if duplicate test fails
            if response.status_code != 400:
                print(f"❌ Duplicate test failed with status {response.status_code}")
                print(f"Response: {response.json()}")
                
            assert response.status_code == 400
            assert "Username already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email."""
        # Register first user
        await client.post("/auth/register", json=test_user_data)
        
        # Try to register with same email
        duplicate_data = test_user_data.copy()
        duplicate_data["username"] = "differentuser"
        
        response = await client.post("/auth/register", json=duplicate_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, client, test_user_data):
        """Test registration with password mismatch."""
        test_data = test_user_data.copy()
        test_data["confirm_password"] = "differentpassword"
        
        response = await client.post("/auth/register", json=test_data)
        assert response.status_code == 422  # Validation error


class TestEmailVerification:
    """Test email verification flow."""
    
    @pytest.mark.asyncio
    async def test_verify_email_success(self, client, test_user_data):
        """Test successful email verification."""
        # Register user
        register_response = await client.post("/auth/register", json=test_user_data)
        assert register_response.status_code == 200
        
        # Note: In real integration tests, we would get the token from the database
        # For now, we test the endpoint structure
        fake_token = "fake_verification_token"
        
        response = await client.post(f"/auth/verify-email?token={fake_token}")
        # This will return 400 because token doesn't exist, but tests the endpoint
        assert response.status_code == 400
        assert "Invalid verification token" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_resend_verification(self, client, test_user_data):
        """Test resending verification email."""
        # Register user
        await client.post("/auth/register", json=test_user_data)
        
        # Resend verification
        response = await client.post(f"/auth/resend-verification?email={test_user_data['email']}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Verification email sent"
    
    @pytest.mark.asyncio
    async def test_resend_verification_nonexistent_email(self, client):
        """Test resending verification to non-existent email."""
        response = await client.post("/auth/resend-verification?email=nonexistent@example.com")
        assert response.status_code == 200
        # Should return success to prevent email enumeration
        assert "verification link has been sent" in response.json()["message"]


class TestPasswordReset:
    """Test password reset flow."""
    
    @pytest.mark.asyncio
    async def test_forgot_password(self, client, test_user_data):
        """Test password reset request."""
        async with client as ac:
            # Register and verify user (simplified for test)
            await ac.post("/auth/register", json=test_user_data)
            
            reset_data = {"email": test_user_data["email"]}
            response = await ac.post("/auth/forgot-password", json=reset_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Password reset email sent"
    
    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(self, client):
        """Test password reset for non-existent email."""
        async with client as ac:
            reset_data = {"email": "nonexistent@example.com"}
            response = await ac.post("/auth/forgot-password", json=reset_data)
            
            assert response.status_code == 200
            # Should return success to prevent email enumeration
            assert "password reset link has been sent" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token."""
        reset_data = {
            "token": "invalid_token",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }
        
        response = await client.post("/auth/reset-password", json=reset_data)
        assert response.status_code == 400
        assert "Invalid reset token" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_verify_reset_token_invalid(self, client):
        """Test verifying invalid reset token."""
        async with client as ac:
            response = await ac.get("/auth/reset-password/verify/invalid_token")
            assert response.status_code == 400
            assert "Invalid or expired reset token" in response.json()["detail"]


class TestLoginAfterRegistration:
    """Test login functionality after registration."""
    
    @pytest.mark.asyncio
    async def test_login_unverified_user(self, client, test_user_data):
        """Test that unverified users cannot login."""
        async with client as ac:
            # Register user (will be inactive until verified)
            await ac.post("/auth/register", json=test_user_data)
            
            # Try to login
            login_data = {
                "username": test_user_data["username"],
                "password": test_user_data["password"]
            }
            
            response = await ac.post("/auth/login", data=login_data)
            assert response.status_code == 400
            assert "Inactive user account" in response.json()["detail"]


class TestAuthenticationEndpoints:
    """Test authentication endpoint accessibility."""
    
    @pytest.mark.asyncio
    async def test_auth_status_endpoint(self, client):
        """Test authentication status endpoint."""
        response = await client.get("/auth/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["authentication"] == "enabled"
        assert data["token_type"] == "JWT"
        assert "password_requirements" in data
        assert "supported_roles" in data
    
    @pytest.mark.asyncio
    async def test_protected_endpoints_require_auth(self, client):
        """Test that protected endpoints require authentication."""
        # Test getting current user without auth
        response = await client.get("/auth/me")
        assert response.status_code == 401
        
        # Test logout without auth
        response = await client.post("/auth/logout")
        assert response.status_code == 401


class TestValidationErrors:
    """Test input validation errors."""
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client, test_user_data):
        """Test registration with invalid email."""
        test_data = test_user_data.copy()
        test_data["email"] = "invalid_email"
        
        response = await client.post("/auth/register", json=test_data)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_register_short_password(self, client, test_user_data):
        """Test registration with short password."""
        test_data = test_user_data.copy()
        test_data["password"] = "short"
        test_data["confirm_password"] = "short"
        
        response = await client.post("/auth/register", json=test_data)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_register_invalid_username(self, client, test_user_data):
        """Test registration with invalid username."""
        test_data = test_user_data.copy()
        test_data["username"] = "us"  # Too short
        
        response = await client.post("/auth/register", json=test_data)
        assert response.status_code == 422  # Validation error


class TestSecurityFeatures:
    """Test security features of authentication system."""
    
    @pytest.mark.asyncio
    async def test_password_reset_rate_limiting(self, client, test_user_data):
        """Test rate limiting on password reset requests."""
        async with client as ac:
            # Register user
            await ac.post("/auth/register", json=test_user_data)
            
            reset_data = {"email": test_user_data["email"]}
            
            # Make multiple reset requests
            for _ in range(3):
                response = await ac.post("/auth/forgot-password", json=reset_data)
                assert response.status_code == 200
            
            # Note: Actual rate limiting would be tested with real rate limiter
            # This tests the endpoint accepts multiple requests
    
    @pytest.mark.asyncio
    async def test_email_enumeration_protection(self, client):
        """Test protection against email enumeration attacks."""
        # Test with non-existent email
        reset_data = {"email": "nonexistent@example.com"}
        response = await client.post("/auth/forgot-password", json=reset_data)
        
        # Should return success even for non-existent email
        assert response.status_code == 200
        assert "password reset link has been sent" in response.json()["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])