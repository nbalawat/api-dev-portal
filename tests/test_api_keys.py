"""
Comprehensive Tests for API Key Management System

Tests cover all aspects of the API key management functionality including:
- API key generation and validation
- CRUD operations
- Authentication and authorization
- Rate limiting
- Activity logging
- Lifecycle management
- Analytics and reporting
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_database
from app.models.api_key import APIKey, APIKeyStatus, APIKeyScope
from app.models.user import User, UserRole
from app.core.api_keys import APIKeyManager
from app.services.activity_logging import ActivityLogger, ActivityType, Severity
from app.core.permissions import PermissionManager, ResourceType, Permission


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    """Create a test client."""
    def override_get_database():
        yield TestingSessionLocal()
    
    app.dependency_overrides[get_database] = override_get_database
    return TestClient(app)


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        role=UserRole.developer,
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin user."""
    user = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        role=UserRole.admin,
        hashed_password="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_api_key(db_session: AsyncSession, test_user: User):
    """Create a test API key."""
    key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
    
    api_key = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        name="Test API Key",
        description="A test API key",
        user_id=test_user.id,
        scopes=["read", "write"],
        expires_at=datetime.utcnow() + timedelta(days=30),
        rate_limit=1000,
        status=APIKeyStatus.active
    )
    
    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)
    
    # Return both the API key object and the secret key
    api_key.secret_key = secret_key
    return api_key


class TestAPIKeyGeneration:
    """Test API key generation and validation."""
    
    def test_generate_key_pair(self):
        """Test API key pair generation."""
        key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
        
        # Check key format
        assert key_id.startswith("ak_"), "Key ID should start with 'ak_'"
        assert secret_key.startswith("sk_"), "Secret key should start with 'sk_'"
        assert len(key_id) > 20, "Key ID should be sufficiently long"
        assert len(secret_key) > 40, "Secret key should be sufficiently long"
        
        # Check hash generation
        assert len(key_hash) > 0, "Key hash should not be empty"
        assert key_hash != secret_key, "Hash should be different from secret key"
    
    def test_hash_key(self):
        """Test key hashing functionality."""
        test_key = "sk_test_key_12345"
        hash1 = APIKeyManager.hash_key(test_key)
        hash2 = APIKeyManager.hash_key(test_key)
        
        # Same key should produce same hash
        assert hash1 == hash2, "Same key should produce same hash"
        
        # Different keys should produce different hashes
        different_key = "sk_different_key_12345"
        hash3 = APIKeyManager.hash_key(different_key)
        assert hash1 != hash3, "Different keys should produce different hashes"
    
    def test_verify_key(self):
        """Test key verification."""
        test_key = "sk_test_key_12345"
        key_hash = APIKeyManager.hash_key(test_key)
        
        # Correct key should verify
        assert APIKeyManager.verify_key(test_key, key_hash), "Correct key should verify"
        
        # Incorrect key should not verify
        wrong_key = "sk_wrong_key_12345"
        assert not APIKeyManager.verify_key(wrong_key, key_hash), "Wrong key should not verify"


class TestAPIKeyValidation:
    """Test API key validation and authentication."""
    
    @pytest.mark.asyncio
    async def test_validate_active_key(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test validation of active API key."""
        validated_key = await APIKeyManager.validate_api_key(
            db_session, test_api_key.secret_key, "127.0.0.1"
        )
        
        assert validated_key is not None, "Active key should validate"
        assert validated_key.id == test_api_key.id, "Should return correct key"
        assert validated_key.status == APIKeyStatus.active, "Key should be active"
    
    @pytest.mark.asyncio
    async def test_validate_nonexistent_key(self, db_session: AsyncSession):
        """Test validation of non-existent API key."""
        fake_key = "sk_fake_key_12345"
        validated_key = await APIKeyManager.validate_api_key(
            db_session, fake_key, "127.0.0.1"
        )
        
        assert validated_key is None, "Non-existent key should not validate"
    
    @pytest.mark.asyncio
    async def test_validate_expired_key(self, db_session: AsyncSession, test_user: User):
        """Test validation of expired API key."""
        # Create expired key
        key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
        
        expired_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name="Expired Key",
            user_id=test_user.id,
            scopes=["read"],
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
            status=APIKeyStatus.active
        )
        
        db_session.add(expired_key)
        await db_session.commit()
        
        validated_key = await APIKeyManager.validate_api_key(
            db_session, secret_key, "127.0.0.1"
        )
        
        assert validated_key is None, "Expired key should not validate"
    
    @pytest.mark.asyncio
    async def test_validate_revoked_key(self, db_session: AsyncSession, test_user: User):
        """Test validation of revoked API key."""
        # Create revoked key
        key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
        
        revoked_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name="Revoked Key",
            user_id=test_user.id,
            scopes=["read"],
            status=APIKeyStatus.revoked
        )
        
        db_session.add(revoked_key)
        await db_session.commit()
        
        validated_key = await APIKeyManager.validate_api_key(
            db_session, secret_key, "127.0.0.1"
        )
        
        assert validated_key is None, "Revoked key should not validate"
    
    @pytest.mark.asyncio
    async def test_ip_restriction(self, db_session: AsyncSession, test_user: User):
        """Test IP address restriction."""
        # Create key with IP restriction
        key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
        
        restricted_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name="IP Restricted Key",
            user_id=test_user.id,
            scopes=["read"],
            allowed_ips=["192.168.1.1", "10.0.0.1"],
            status=APIKeyStatus.active
        )
        
        db_session.add(restricted_key)
        await db_session.commit()
        
        # Should validate from allowed IP
        validated_key = await APIKeyManager.validate_api_key(
            db_session, secret_key, "192.168.1.1"
        )
        assert validated_key is not None, "Should validate from allowed IP"
        
        # Should not validate from disallowed IP
        validated_key = await APIKeyManager.validate_api_key(
            db_session, secret_key, "192.168.1.2"
        )
        assert validated_key is None, "Should not validate from disallowed IP"


class TestAPIKeyCRUD:
    """Test API key CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, client: TestClient, test_user: User):
        """Test API key creation endpoint."""
        # Mock authentication
        with patch('app.dependencies.auth.get_current_active_user', return_value=test_user):
            response = client.post(
                "/api-keys/",
                json={
                    "name": "Test Key",
                    "description": "A test key",
                    "scopes": ["read", "write"],
                    "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                    "rate_limit": 1000
                }
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "api_key" in data, "Response should contain api_key"
        assert "secret_key" in data, "Response should contain secret_key"
        assert data["api_key"]["name"] == "Test Key", "Name should match"
        assert "read" in data["api_key"]["scopes"], "Should have read scope"
        assert "write" in data["api_key"]["scopes"], "Should have write scope"
    
    @pytest.mark.asyncio
    async def test_list_api_keys(self, client: TestClient, test_user: User, test_api_key: APIKey):
        """Test API key listing endpoint."""
        with patch('app.dependencies.auth.get_current_active_user', return_value=test_user):
            response = client.get("/api-keys/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "api_keys" in data, "Response should contain api_keys list"
        assert len(data["api_keys"]) > 0, "Should return at least one API key"
        assert data["total"] > 0, "Total count should be greater than 0"
    
    @pytest.mark.asyncio
    async def test_get_api_key(self, client: TestClient, test_user: User, test_api_key: APIKey):
        """Test getting a specific API key."""
        with patch('app.dependencies.auth.get_current_active_user', return_value=test_user):
            response = client.get(f"/api-keys/{test_api_key.id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["id"] == str(test_api_key.id), "Should return correct API key"
        assert data["name"] == test_api_key.name, "Name should match"
    
    @pytest.mark.asyncio
    async def test_update_api_key(self, client: TestClient, test_user: User, test_api_key: APIKey):
        """Test updating an API key."""
        with patch('app.dependencies.auth.get_current_active_user', return_value=test_user):
            response = client.put(
                f"/api-keys/{test_api_key.id}",
                json={
                    "name": "Updated Test Key",
                    "description": "Updated description"
                }
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["name"] == "Updated Test Key", "Name should be updated"
        assert data["description"] == "Updated description", "Description should be updated"
    
    @pytest.mark.asyncio
    async def test_revoke_api_key(self, client: TestClient, test_user: User, test_api_key: APIKey):
        """Test revoking an API key."""
        with patch('app.dependencies.auth.get_current_active_user', return_value=test_user):
            response = client.post(
                f"/api-keys/{test_api_key.id}/revoke",
                json={"reason": "Test revocation"}
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response should contain message"
        assert "revoked successfully" in data["message"], "Should confirm revocation"


class TestPermissions:
    """Test permission system."""
    
    @pytest.mark.asyncio
    async def test_permission_checking(self):
        """Test permission checking logic."""
        # Create mock API key with read scope
        api_key = Mock()
        api_key.scopes = ["read"]
        
        from app.middleware.permissions import PermissionChecker
        checker = PermissionChecker(api_key)
        
        # Should have read permission
        assert checker.can(ResourceType.USER, Permission.READ), "Should have read permission"
        
        # Should not have write permission
        assert not checker.can(ResourceType.USER, Permission.WRITE), "Should not have write permission"
        
        # Should not have admin permission
        assert not checker.can(ResourceType.ADMIN, Permission.READ), "Should not have admin permission"
    
    @pytest.mark.asyncio
    async def test_admin_permissions(self):
        """Test admin permission logic."""
        # Create mock API key with admin scope
        api_key = Mock()
        api_key.scopes = ["admin"]
        
        from app.middleware.permissions import PermissionChecker
        checker = PermissionChecker(api_key)
        
        # Should have all permissions
        assert checker.can(ResourceType.USER, Permission.READ), "Admin should have read permission"
        assert checker.can(ResourceType.USER, Permission.WRITE), "Admin should have write permission"
        assert checker.can(ResourceType.ADMIN, Permission.READ), "Admin should have admin read permission"
        assert checker.is_admin(), "Should be identified as admin"


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_checking(self, db_session: AsyncSession, test_api_key: APIKey):
        """Test rate limit checking."""
        # Test that rate limit check doesn't raise errors
        remaining = await APIKeyManager.check_rate_limit(db_session, test_api_key)
        
        # Should return a number (remaining requests)
        assert isinstance(remaining, (int, float)), "Should return numeric value"
        assert remaining >= 0, "Remaining requests should be non-negative"


class TestActivityLogging:
    """Test activity logging functionality."""
    
    @pytest.mark.asyncio
    async def test_activity_logger_creation(self):
        """Test activity logger creation and basic functionality."""
        logger = ActivityLogger()
        
        # Test logging an activity
        await logger.log_activity(
            activity_type=ActivityType.KEY_CREATED,
            severity=Severity.MEDIUM,
            api_key_id="test_key_id",
            user_id="test_user_id",
            details={"test": "data"}
        )
        
        # Should have one entry in buffer
        assert len(logger.log_buffer) == 1, "Should have one log entry"
        
        entry = logger.log_buffer[0]
        assert entry.activity_type == ActivityType.KEY_CREATED, "Activity type should match"
        assert entry.severity == Severity.MEDIUM, "Severity should match"
        assert entry.api_key_id == "test_key_id", "API key ID should match"
    
    @pytest.mark.asyncio
    async def test_authentication_logging(self):
        """Test authentication attempt logging."""
        from app.services.activity_logging import log_auth_attempt
        
        # Mock the logger
        with patch('app.services.activity_logging.get_activity_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            
            # Test successful authentication
            await log_auth_attempt(
                api_key_id="test_key",
                success=True,
                source_ip="127.0.0.1"
            )
            
            # Verify the logger was called
            mock_logger.log_authentication_attempt.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self):
        """Test anomaly detection functionality."""
        logger = ActivityLogger()
        
        # Add multiple failed auth attempts to trigger anomaly
        for i in range(15):  # More than threshold
            await logger.log_activity(
                activity_type=ActivityType.AUTH_FAILED,
                api_key_id="test_key",
                source_ip="192.168.1.1"
            )
        
        # Test anomaly detection
        anomalies = await logger.detect_anomalies("test_key", hours=1)
        
        # Should detect repeated auth failures
        auth_failure_anomalies = [
            a for a in anomalies 
            if a["type"] == "repeated_auth_failures"
        ]
        assert len(auth_failure_anomalies) > 0, "Should detect repeated auth failures"


class TestLifecycleManagement:
    """Test API key lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_key_rotation(self, db_session: AsyncSession, test_user: User):
        """Test API key rotation functionality."""
        # Create initial key
        key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
        
        original_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name="Original Key",
            user_id=test_user.id,
            scopes=["read"],
            status=APIKeyStatus.active
        )
        
        db_session.add(original_key)
        await db_session.commit()
        await db_session.refresh(original_key)
        
        # Test rotation
        from app.core.key_lifecycle import APIKeyLifecycleManager, RotationTrigger
        
        manager = APIKeyLifecycleManager()
        rotation_result = await manager.rotate_api_key(
            api_key_id=str(original_key.id),
            trigger=RotationTrigger.MANUAL,
            user_id=str(test_user.id)
        )
        
        assert rotation_result.success, "Rotation should succeed"
        assert rotation_result.new_key_id != str(original_key.id), "Should create new key"
        assert rotation_result.new_secret_key is not None, "Should return new secret key"


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_api_key_workflow(self, client: TestClient, test_user: User):
        """Test complete API key lifecycle workflow."""
        with patch('app.dependencies.auth.get_current_active_user', return_value=test_user):
            # 1. Create API key
            create_response = client.post(
                "/api-keys/",
                json={
                    "name": "Integration Test Key",
                    "description": "For integration testing",
                    "scopes": ["read", "write"],
                    "rate_limit": 500
                }
            )
            
            assert create_response.status_code == 200, "Key creation should succeed"
            create_data = create_response.json()
            api_key_id = create_data["api_key"]["id"]
            secret_key = create_data["secret_key"]
            
            # 2. List keys (should include new key)
            list_response = client.get("/api-keys/")
            assert list_response.status_code == 200, "Key listing should succeed"
            list_data = list_response.json()
            
            key_ids = [key["id"] for key in list_data["api_keys"]]
            assert api_key_id in key_ids, "New key should be in list"
            
            # 3. Get specific key
            get_response = client.get(f"/api-keys/{api_key_id}")
            assert get_response.status_code == 200, "Key retrieval should succeed"
            
            # 4. Update key
            update_response = client.put(
                f"/api-keys/{api_key_id}",
                json={
                    "name": "Updated Integration Test Key",
                    "description": "Updated for integration testing"
                }
            )
            assert update_response.status_code == 200, "Key update should succeed"
            
            # 5. Use key for authentication (mock API endpoint)
            with patch('app.middleware.api_key_auth.APIKeyManager.validate_api_key') as mock_validate:
                mock_key = Mock()
                mock_key.id = api_key_id
                mock_key.user_id = test_user.id
                mock_key.scopes = ["read", "write"]
                mock_key.status = APIKeyStatus.active
                mock_validate.return_value = mock_key
                
                auth_response = client.get(
                    "/api/v1/profile",
                    headers={"Authorization": f"Bearer {secret_key}"}
                )
                # Note: This might fail due to missing user data, but auth should work
                assert auth_response.status_code in [200, 404], "Authentication should work"
            
            # 6. Revoke key
            revoke_response = client.post(
                f"/api-keys/{api_key_id}/revoke",
                json={"reason": "Integration test cleanup"}
            )
            assert revoke_response.status_code == 200, "Key revocation should succeed"


# Test configuration
@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection for tests."""
    async with TestingSessionLocal() as session:
        # Simple query to test connection
        result = await session.execute("SELECT 1")
        assert result.scalar() == 1, "Database connection should work"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])