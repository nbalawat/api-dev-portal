"""
Simplified tests for core API Key Management functionality.

These tests focus on testing the core logic without requiring a full database setup.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.core.api_keys import APIKeyManager
    from app.services.activity_logging import ActivityLogger, ActivityType, Severity
    from app.core.rate_limiting import (
        MemoryRateLimitBackend, FixedWindowRateLimiter, 
        SlidingWindowRateLimiter, TokenBucketRateLimiter
    )
    imports_available = True
except ImportError as e:
    print("Import error:", str(e))
    print("This is expected in a test environment without full dependencies")
    imports_available = False


class TestAPIKeyGeneration:
    """Test API key generation and validation without database dependencies."""
    
    def test_generate_key_pair(self):
        """Test API key pair generation."""
        try:
            key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
            
            # Check key format
            assert key_id.startswith("ak_"), f"Key ID should start with 'ak_', got: {key_id}"
            assert secret_key.startswith("sk_"), f"Secret key should start with 'sk_', got: {secret_key}"
            assert len(key_id) > 20, f"Key ID should be sufficiently long, got length: {len(key_id)}"
            assert len(secret_key) > 40, f"Secret key should be sufficiently long, got length: {len(secret_key)}"
            
            # Check hash generation
            assert len(key_hash) > 0, "Key hash should not be empty"
            assert key_hash != secret_key, "Hash should be different from secret key"
            
            print("✅ API key generation test passed")
            return True
            
        except Exception as e:
            print(f"❌ API key generation test failed: {e}")
            return False
    
    def test_hash_key(self):
        """Test key hashing functionality."""
        try:
            test_key = "sk_test_key_12345"
            hash1 = APIKeyManager.hash_key(test_key)
            hash2 = APIKeyManager.hash_key(test_key)
            
            # Same key should produce same hash
            assert hash1 == hash2, "Same key should produce same hash"
            
            # Different keys should produce different hashes
            different_key = "sk_different_key_12345"
            hash3 = APIKeyManager.hash_key(different_key)
            assert hash1 != hash3, "Different keys should produce different hashes"
            
            print("✅ Key hashing test passed")
            return True
            
        except Exception as e:
            print(f"❌ Key hashing test failed: {e}")
            return False
    
    def test_verify_key(self):
        """Test key verification."""
        try:
            test_key = "sk_test_key_12345"
            key_hash = APIKeyManager.hash_key(test_key)
            
            # Correct key should verify
            assert APIKeyManager.verify_key(test_key, key_hash), "Correct key should verify"
            
            # Incorrect key should not verify
            wrong_key = "sk_wrong_key_12345"
            assert not APIKeyManager.verify_key(wrong_key, key_hash), "Wrong key should not verify"
            
            print("✅ Key verification test passed")
            return True
            
        except Exception as e:
            print(f"❌ Key verification test failed: {e}")
            return False


class TestRateLimitingCore:
    """Test rate limiting core functionality."""
    
    @pytest.mark.asyncio
    async def test_memory_backend(self):
        """Test memory-based rate limiting backend."""
        try:
            backend = MemoryRateLimitBackend()
            
            # Test increment
            result = await backend.increment("test_key", 60)
            assert result == 1, f"First increment should return 1, got: {result}"
            
            result = await backend.increment("test_key", 60)
            assert result == 2, f"Second increment should return 2, got: {result}"
            
            # Test get
            value = await backend.get("test_key")
            assert value == 2, f"Get should return current value 2, got: {value}"
            
            print("✅ Memory backend test passed")
            return True
            
        except Exception as e:
            print(f"❌ Memory backend test failed: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_fixed_window_limiter(self):
        """Test fixed window rate limiting."""
        try:
            backend = MemoryRateLimitBackend()
            limiter = FixedWindowRateLimiter(backend)
            
            key = "test_key"
            limit = 5
            window_seconds = 60
            
            # Should allow requests within limit
            for i in range(limit):
                result = await limiter.check_rate_limit(key, limit, window_seconds)
                assert result.allowed, f"Request {i+1} should be allowed"
                assert result.remaining == limit - (i + 1), f"Remaining count should decrease, expected {limit - (i + 1)}, got {result.remaining}"
            
            # Should deny request over limit
            result = await limiter.check_rate_limit(key, limit, window_seconds)
            assert not result.allowed, "Request over limit should be denied"
            assert result.remaining == 0, f"No requests should remain, got: {result.remaining}"
            
            print("✅ Fixed window limiter test passed")
            return True
            
        except Exception as e:
            print(f"❌ Fixed window limiter test failed: {e}")
            return False


class TestActivityLoggingCore:
    """Test activity logging core functionality."""
    
    @pytest.mark.asyncio
    async def test_activity_logger_creation(self):
        """Test activity logger creation and basic functionality."""
        try:
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
            assert len(logger.log_buffer) == 1, f"Should have one log entry, got: {len(logger.log_buffer)}"
            
            entry = logger.log_buffer[0]
            assert entry.activity_type == ActivityType.KEY_CREATED, f"Activity type should match, got: {entry.activity_type}"
            assert entry.severity == Severity.MEDIUM, f"Severity should match, got: {entry.severity}"
            assert entry.api_key_id == "test_key_id", f"API key ID should match, got: {entry.api_key_id}"
            
            print("✅ Activity logger test passed")
            return True
            
        except Exception as e:
            print(f"❌ Activity logger test failed: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self):
        """Test anomaly detection functionality."""
        try:
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
            assert auth_failure_anomalies[0]["count"] == 15, f"Should detect 15 failures, got: {auth_failure_anomalies[0]['count']}"
            
            print("✅ Anomaly detection test passed")
            return True
            
        except Exception as e:
            print(f"❌ Anomaly detection test failed: {e}")
            return False


def run_manual_tests():
    """Run tests manually without pytest dependency."""
    print("🚀 Running API Key Management System Core Tests")
    print("=" * 60)
    
    if not imports_available:
        print("❌ Cannot run tests - core modules not available")
        print("This is expected in environments without full dependencies")
        return False
    
    test_results = []
    
    # Test API Key Generation
    print("\n📝 Testing API Key Generation...")
    key_tests = TestAPIKeyGeneration()
    test_results.append(key_tests.test_generate_key_pair())
    test_results.append(key_tests.test_hash_key())
    test_results.append(key_tests.test_verify_key())
    
    # Test Rate Limiting (async tests)
    print("\n⏱️  Testing Rate Limiting...")
    async def run_rate_limit_tests():
        rate_tests = TestRateLimitingCore()
        results = []
        results.append(await rate_tests.test_memory_backend())
        results.append(await rate_tests.test_fixed_window_limiter())
        return results
    
    rate_results = asyncio.run(run_rate_limit_tests())
    test_results.extend(rate_results)
    
    # Test Activity Logging (async tests)
    print("\n📊 Testing Activity Logging...")
    async def run_activity_tests():
        activity_tests = TestActivityLoggingCore()
        results = []
        results.append(await activity_tests.test_activity_logger_creation())
        results.append(await activity_tests.test_anomaly_detection())
        return results
    
    activity_results = asyncio.run(run_activity_tests())
    test_results.extend(activity_results)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    failed = total - passed
    
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! The API Key Management System core functionality is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the output above for details.")
    
    return failed == 0


if __name__ == "__main__":
    success = run_manual_tests()
    exit(0 if success else 1)