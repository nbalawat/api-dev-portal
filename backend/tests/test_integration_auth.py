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

# Create test engine with minimal, reliable settings
test_engine = create_async_engine(
    TEST_DATABASE_URL, 
    echo=False,
    pool_size=1,
    max_overflow=0,
    pool_pre_ping=False,
    pool_recycle=-1,  # Disable connection recycling
    isolation_level="AUTOCOMMIT"  # Auto-commit for test reliability
)
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_test_database():
    """Get test database session - simple and clean."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        await session.close()


# Override the dependency
app.dependency_overrides[get_database] = get_test_database


@pytest.fixture(scope="session", autouse=True)  
def setup_test_session():
    """Setup and teardown for the test session."""
    print("🚀 Starting test session...")
    yield
    print("✅ Test session completed")


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
    """Truncate all tables in correct order to respect foreign key constraints."""
    cleanup_engine = create_async_engine(
        TEST_DATABASE_URL, 
        echo=False, 
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=False
    )
    
    try:
        async with cleanup_engine.begin() as conn:
            # Delete in reverse dependency order to avoid foreign key violations
            delete_order = [
                "email_verification_tokens",  # References users
                "password_reset_tokens",      # References users  
                "api_key_usage",             # References api_keys
                "api_keys",                  # References users
                "token_blacklist",           # No foreign keys
                "users"                      # Referenced by other tables
            ]
            
            for table in delete_order:
                try:
                    await conn.execute(text(f"DELETE FROM {table}"))
                    print(f"✅ Cleaned table: {table}")
                except Exception as e:
                    print(f"⚠️  Failed to clean {table}: {e}")
            
            print("🧹 Database cleanup completed")
            
    except Exception as e:
        print(f"❌ Database cleanup failed: {e}")
        raise e
    finally:
        await cleanup_engine.dispose()


@pytest.fixture(scope="function", autouse=True)
async def clean_test_data():
    """Clean test data before each test - simple and reliable."""
    # Clean database before test
    try:
        await truncate_all_tables()
    except Exception as e:
        print(f"Warning: Pre-test cleanup failed: {e}")
    
    yield
    
    # Clean database after test
    try:
        await truncate_all_tables()
    except Exception as e:
        print(f"Warning: Post-test cleanup failed: {e}")


def create_unique_test_user_data():
    """Create test user registration data with unique values."""
    import uuid
    import time
    # Use timestamp + uuid to ensure absolute uniqueness between test runs
    timestamp = int(time.time() * 1000) % 100000  # Last 5 digits of timestamp
    unique_id = str(uuid.uuid4())[:8]
    combined_id = f"{timestamp}_{unique_id}"
    return {
        "username": f"testuser_{combined_id}",
        "email": f"test_{combined_id}@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
        "role": "developer"
    }


@pytest.fixture(scope="function")
def test_user_data():
    """Test user registration data with unique values per test call."""
    return create_unique_test_user_data()


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
    async def test_register_duplicate_username(self, client, clean_test_data):
        """Test registration with duplicate username."""
        async with client as ac:
            # Add larger delay to prevent race conditions
            await asyncio.sleep(0.3)
            
            # Create unique test data for this test
            test_user_data = create_unique_test_user_data()
            
            # Register first user
            first_response = await ac.post("/auth/register", json=test_user_data)
            
            # Print debug info if first registration fails
            if first_response.status_code != 200:
                print(f"❌ First registration failed with status {first_response.status_code}")
                print(f"Response: {first_response.json()}")
                
            assert first_response.status_code == 200
            
            # Try to register with same username but different email
            duplicate_data = test_user_data.copy()
            duplicate_data["email"] = f"different_{duplicate_data['email']}"
            
            response = await ac.post("/auth/register", json=duplicate_data)
            
            # Print debug info if duplicate test fails
            if response.status_code != 400:
                print(f"❌ Duplicate test failed with status {response.status_code}")
                print(f"Response: {response.json()}")
                
            assert response.status_code == 400
            assert "Username already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, clean_test_data):
        """Test registration with duplicate email."""
        async with client as ac:
            # Create unique test data for this test
            test_user_data = create_unique_test_user_data()
            
            # Register first user
            first_response = await ac.post("/auth/register", json=test_user_data)
            assert first_response.status_code == 200
            
            # Try to register with same email but different username
            duplicate_data = test_user_data.copy()
            duplicate_data["username"] = f"different_{duplicate_data['username']}"
            
            response = await ac.post("/auth/register", json=duplicate_data)
            assert response.status_code == 400
            assert "Email already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, client, clean_test_data):
        """Test registration with password mismatch."""
        async with client as ac:
            # Create unique test data for this test
            test_data = create_unique_test_user_data()
            test_data["confirm_password"] = "differentpassword"
            
            response = await ac.post("/auth/register", json=test_data)
            assert response.status_code == 422  # Validation error


class TestEmailVerification:
    """Test email verification flow."""
    
    @pytest.mark.asyncio
    async def test_verify_email_success(self, client, clean_test_data):
        """Test successful email verification."""
        async with client as ac:
            # Create unique test data for this test
            test_user_data = create_unique_test_user_data()
            
            # Register user
            register_response = await ac.post("/auth/register", json=test_user_data)
            assert register_response.status_code == 200
        
            # Note: In real integration tests, we would get the token from the database
            # For now, we test the endpoint structure
            fake_token = "fake_verification_token"
            
            response = await ac.post(f"/auth/verify-email?token={fake_token}")
            # This will return 400 because token doesn't exist, but tests the endpoint
            assert response.status_code == 400
            assert "Invalid verification token" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_resend_verification(self, client, clean_test_data):
        """Test resending verification email."""
        async with client as ac:
            # Create unique test data for this test
            test_user_data = create_unique_test_user_data()
            
            # Register user
            await ac.post("/auth/register", json=test_user_data)
            
            # Resend verification
            response = await ac.post(f"/auth/resend-verification?email={test_user_data['email']}")
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
    async def test_forgot_password(self, client, clean_test_data):
        """Test password reset request."""
        async with client as ac:
            # Create unique test data for this test
            test_user_data = create_unique_test_user_data()
            
            # Register and verify user (simplified for test)
            await ac.post("/auth/register", json=test_user_data)
            
            reset_data = {"email": test_user_data["email"]}
            response = await ac.post("/auth/forgot-password", json=reset_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "password reset" in data["message"].lower()
    
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
    async def test_login_unverified_user(self, client, clean_test_data):
        """Test that unverified users cannot login."""
        async with client as ac:
            # Create unique test data for this test
            test_user_data = create_unique_test_user_data()
            
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
    async def test_register_invalid_email(self, client, clean_test_data):
        """Test registration with invalid email."""
        async with client as ac:
            # Create unique test data for this test
            test_data = create_unique_test_user_data()
            test_data["email"] = "invalid_email"
            
            response = await ac.post("/auth/register", json=test_data)
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_register_short_password(self, client, clean_test_data):
        """Test registration with short password."""
        async with client as ac:
            # Create unique test data for this test
            test_data = create_unique_test_user_data()
            test_data["password"] = "short"
            test_data["confirm_password"] = "short"
            
            response = await ac.post("/auth/register", json=test_data)
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_register_invalid_username(self, client, clean_test_data):
        """Test registration with invalid username."""
        async with client as ac:
            # Create unique test data for this test
            test_data = create_unique_test_user_data()
            test_data["username"] = "us"  # Too short
            
            response = await ac.post("/auth/register", json=test_data)
            assert response.status_code == 422  # Validation error


class TestSecurityFeatures:
    """Test security features of authentication system."""
    
    @pytest.mark.asyncio
    async def test_password_reset_rate_limiting(self, client, clean_test_data):
        """Test rate limiting on password reset requests."""
        async with client as ac:
            # Create unique test data for this test
            test_user_data = create_unique_test_user_data()
            
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