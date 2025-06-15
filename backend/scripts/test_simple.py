#!/usr/bin/env python3
"""
Simple test script for API Key Management System core functionality.
This script tests the core logic without external dependencies.
"""
import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test if we can import the core modules."""
    print("Testing imports...")
    try:
        # Test core API key functionality
        from core.api_keys import APIKeyManager
        print("✅ APIKeyManager imported successfully")
        
        # Test activity logging
        from services.activity_logging import ActivityLogger, ActivityType, Severity
        print("✅ Activity logging components imported successfully")
        
        # Test rate limiting
        from core.rate_limiting import MemoryRateLimitBackend, FixedWindowRateLimiter
        print("✅ Rate limiting components imported successfully")
        
        return True, {
            'APIKeyManager': APIKeyManager,
            'ActivityLogger': ActivityLogger,
            'ActivityType': ActivityType,
            'Severity': Severity,
            'MemoryRateLimitBackend': MemoryRateLimitBackend,
            'FixedWindowRateLimiter': FixedWindowRateLimiter
        }
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False, None

def test_api_key_generation(APIKeyManager):
    """Test API key generation functionality."""
    print("\nTesting API key generation...")
    
    try:
        # Test key pair generation
        key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
        
        # Check key format
        assert key_id.startswith("ak_"), f"Key ID should start with 'ak_', got: {key_id}"
        assert secret_key.startswith("sk_"), f"Secret key should start with 'sk_', got: {secret_key}"
        assert len(key_id) > 20, f"Key ID should be sufficiently long, got length: {len(key_id)}"
        assert len(secret_key) > 40, f"Secret key should be sufficiently long, got length: {len(secret_key)}"
        
        print(f"✅ Generated key ID: {key_id}")
        print(f"✅ Generated secret key: {secret_key[:20]}...")
        print(f"✅ Generated hash: {key_hash[:20]}...")
        
        # Test key hashing
        test_key = "sk_test_key_12345"
        hash1 = APIKeyManager.hash_key(test_key)
        hash2 = APIKeyManager.hash_key(test_key)
        
        assert hash1 == hash2, "Same key should produce same hash"
        print("✅ Key hashing is consistent")
        
        # Test key verification
        assert APIKeyManager.verify_key(test_key, hash1), "Correct key should verify"
        assert not APIKeyManager.verify_key("wrong_key", hash1), "Wrong key should not verify"
        print("✅ Key verification works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ API key generation test failed: {e}")
        return False

async def test_rate_limiting(MemoryRateLimitBackend, FixedWindowRateLimiter):
    """Test rate limiting functionality."""
    print("\nTesting rate limiting...")
    
    try:
        # Test memory backend
        backend = MemoryRateLimitBackend()
        
        # Test increment
        result = await backend.increment("test_key", 60)
        assert result == 1, f"First increment should return 1, got: {result}"
        
        result = await backend.increment("test_key", 60)
        assert result == 2, f"Second increment should return 2, got: {result}"
        
        print("✅ Memory backend increment works")
        
        # Test get
        value = await backend.get("test_key")
        assert value == 2, f"Get should return current value 2, got: {value}"
        
        print("✅ Memory backend get works")
        
        # Test rate limiter
        limiter = FixedWindowRateLimiter(backend)
        
        key = "test_rate_limit"
        limit = 3
        window_seconds = 60
        
        # Should allow requests within limit
        for i in range(limit):
            result = await limiter.check_rate_limit(key, limit, window_seconds)
            assert result.allowed, f"Request {i+1} should be allowed"
            print(f"✅ Request {i+1}: allowed={result.allowed}, remaining={result.remaining}")
        
        # Should deny request over limit
        result = await limiter.check_rate_limit(key, limit, window_seconds)
        assert not result.allowed, "Request over limit should be denied"
        print(f"✅ Rate limit exceeded: allowed={result.allowed}, remaining={result.remaining}")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

async def test_activity_logging(ActivityLogger, ActivityType, Severity):
    """Test activity logging functionality."""
    print("\nTesting activity logging...")
    
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
        assert entry.activity_type == ActivityType.KEY_CREATED, f"Activity type should match"
        assert entry.severity == Severity.MEDIUM, f"Severity should match"
        assert entry.api_key_id == "test_key_id", f"API key ID should match"
        
        print("✅ Activity logging works")
        print(f"✅ Logged entry: {entry.activity_type.value} - {entry.severity.value}")
        
        # Test anomaly detection with multiple failed auth attempts
        for i in range(12):  # More than threshold
            await logger.log_activity(
                activity_type=ActivityType.AUTH_FAILED,
                api_key_id="suspicious_key",
                source_ip="192.168.1.1"
            )
        
        # Test anomaly detection
        anomalies = await logger.detect_anomalies("suspicious_key", hours=1)
        
        # Should detect repeated auth failures
        auth_failure_anomalies = [
            a for a in anomalies 
            if a["type"] == "repeated_auth_failures"
        ]
        assert len(auth_failure_anomalies) > 0, "Should detect repeated auth failures"
        print(f"✅ Anomaly detection works: found {len(anomalies)} anomalies")
        
        return True
        
    except Exception as e:
        print(f"❌ Activity logging test failed: {e}")
        return False

def test_core_logic():
    """Test basic logic without external dependencies."""
    print("\nTesting core logic patterns...")
    
    try:
        # Test HMAC-like hashing (simplified)
        import hashlib
        import hmac
        
        test_key = "test_secret_key"
        salt = "test_salt"
        
        # Test consistent hashing
        hash1 = hmac.new(salt.encode(), test_key.encode(), hashlib.sha256).hexdigest()
        hash2 = hmac.new(salt.encode(), test_key.encode(), hashlib.sha256).hexdigest()
        
        assert hash1 == hash2, "HMAC should be consistent"
        print("✅ HMAC hashing works consistently")
        
        # Test different keys produce different hashes
        different_key = "different_secret_key"
        hash3 = hmac.new(salt.encode(), different_key.encode(), hashlib.sha256).hexdigest()
        
        assert hash1 != hash3, "Different keys should produce different hashes"
        print("✅ HMAC produces different hashes for different keys")
        
        # Test key format validation
        def validate_key_format(key):
            return key.startswith("sk_") and len(key) > 10
        
        assert validate_key_format("sk_valid_key_123"), "Valid key should pass validation"
        assert not validate_key_format("invalid_key"), "Invalid key should fail validation"
        assert not validate_key_format("sk_short"), "Short key should fail validation"
        
        print("✅ Key format validation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Core logic test failed: {e}")
        return False

async def run_async_tests(modules):
    """Run async tests."""
    results = []
    
    if modules:
        results.append(await test_rate_limiting(
            modules['MemoryRateLimitBackend'], 
            modules['FixedWindowRateLimiter']
        ))
        
        results.append(await test_activity_logging(
            modules['ActivityLogger'],
            modules['ActivityType'],
            modules['Severity']
        ))
    
    return results

def main():
    """Main test runner."""
    print("🚀 API Key Management System - Simple Tests")
    print("=" * 60)
    
    test_results = []
    
    # Test imports
    imports_success, modules = test_imports()
    test_results.append(imports_success)
    
    # Test core logic (no dependencies)
    test_results.append(test_core_logic())
    
    if imports_success and modules:
        # Test API key generation
        test_results.append(test_api_key_generation(modules['APIKeyManager']))
        
        # Run async tests
        async_results = asyncio.run(run_async_tests(modules))
        test_results.extend(async_results)
    else:
        print("\n⚠️  Skipping module-dependent tests due to import failures")
        print("This is expected in environments without full dependencies")
    
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
        print("\n🎉 All tests passed!")
        print("The API Key Management System core functionality is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed.")
        if not imports_success:
            print("Import failures are expected without full dependency installation.")
    
    print("\n📝 Note: These tests validate core logic and patterns.")
    print("Full integration tests require database and dependency setup.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)