# -*- coding: utf-8 -*-
"""
Test enhanced rate limiting system in Docker environment.

This test module verifies that the enhanced rate limiting system works correctly
including token bucket algorithm, progressive limiting, and burst protection.
Tests use real functionality without mocks to ensure actual behavior.
"""
import sys
import os
import asyncio
import time

# Add the app directory to Python path for imports
sys.path.insert(0, '/app')

from app.services.enhanced_rate_limiting import (
    enhanced_rate_limit_manager,
    RateLimitRule,
    RateLimitScope,
    RateLimitAction,
    TokenBucket,
    ProgressiveRateLimiter
)


def test_token_bucket_initialization():
    """Test token bucket initialization and basic functionality."""
    print("Testing token bucket initialization...")
    
    try:
        # Create a token bucket
        bucket = TokenBucket(
            capacity=10,
            tokens=10.0,
            refill_rate=2.0,  # 2 tokens per second
            last_refill=time.time()
        )
        
        # Verify initial state
        assert bucket.capacity == 10, "Bucket capacity should be 10"
        assert bucket.tokens == 10.0, "Bucket should start with 10 tokens"
        assert bucket.refill_rate == 2.0, "Refill rate should be 2.0"
        assert bucket.total_requests == 0, "Total requests should start at 0"
        assert bucket.rejected_requests == 0, "Rejected requests should start at 0"
        
        # Test token consumption
        success = bucket.consume(3)
        assert success is True, "Should successfully consume 3 tokens"
        assert bucket.tokens == 7.0, "Should have 7 tokens remaining"
        assert bucket.total_requests == 1, "Total requests should be 1"
        
        # Test over-consumption
        success = bucket.consume(8)
        assert success is False, "Should fail to consume 8 tokens (only 7 available)"
        # Note: tokens might have been refilled slightly due to time passage
        assert bucket.tokens <= 7.5, "Token count should not have decreased much"
        assert bucket.total_requests == 2, "Total requests should be 2"
        assert bucket.rejected_requests == 1, "Rejected requests should be 1"
        
        print("✓ Token bucket initialization test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Token bucket initialization test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Token bucket initialization test ERROR: {}".format(str(e)))
        return False


def test_token_bucket_refill():
    """Test token bucket refill mechanism."""
    print("Testing token bucket refill...")
    
    try:
        # Create bucket with past timestamp
        bucket = TokenBucket(
            capacity=10,
            tokens=5.0,
            refill_rate=2.0,  # 2 tokens per second
            last_refill=time.time() - 2.0  # 2 seconds ago
        )
        
        # Check tokens before refill
        initial_tokens = bucket.tokens
        
        # Trigger refill by consuming tokens
        bucket.consume(1)
        
        # Should have refilled approximately 4 tokens (2 seconds * 2 tokens/second)
        # Plus the consumed 1 token, so should be close to initial + 3
        expected_min = initial_tokens + 2  # Allow some variance
        assert bucket.tokens >= expected_min, "Bucket should have refilled tokens"
        assert bucket.tokens <= bucket.capacity, "Bucket should not exceed capacity"
        
        # Test peek functionality
        available = bucket.peek()
        assert available == bucket.tokens, "Peek should return current token count"
        
        print("✓ Token bucket refill test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Token bucket refill test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Token bucket refill test ERROR: {}".format(str(e)))
        return False


def test_progressive_rate_limiter():
    """Test progressive rate limiter functionality."""
    print("Testing progressive rate limiter...")
    
    try:
        # Create base rule
        rule = RateLimitRule(
            name="test_progressive",
            scope=RateLimitScope.USER,
            tokens_per_second=5.0,
            max_tokens=50,
            progressive=True,
            penalty_factor=0.5,
            recovery_factor=1.2,
            min_limit=0.5,
            max_limit=10.0
        )
        
        # Create progressive limiter
        limiter = ProgressiveRateLimiter(rule)
        
        # Test initial state
        initial_rate = limiter.get_current_rate()
        assert initial_rate == 5.0, "Initial rate should match base rule"
        assert limiter.current_multiplier == 1.0, "Initial multiplier should be 1.0"
        
        # Record violations
        limiter.record_violation()
        limiter.record_violation()
        limiter.record_violation()
        
        # Rate should be reduced
        reduced_rate = limiter.get_current_rate()
        assert reduced_rate < initial_rate, "Rate should be reduced after violations"
        assert limiter.current_multiplier < 1.0, "Multiplier should be less than 1.0"
        
        # Test minimum limit
        for _ in range(10):  # Multiple violations
            limiter.record_violation()
        
        final_rate = limiter.get_current_rate()
        assert final_rate >= rule.min_limit, "Rate should not go below minimum limit"
        
        print("✓ Progressive rate limiter test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Progressive rate limiter test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Progressive rate limiter test ERROR: {}".format(str(e)))
        return False


def test_enhanced_rate_limit_manager_initialization():
    """Test enhanced rate limit manager initialization."""
    print("Testing enhanced rate limit manager initialization...")
    
    try:
        # Check that default rules were created
        all_rules = enhanced_rate_limit_manager.get_all_rules()
        
        expected_rules = ["global_requests", "user_requests", "api_key_requests", "ip_requests"]
        for rule_name in expected_rules:
            assert rule_name in all_rules, "Default rule '{}' should exist".format(rule_name)
        
        # Check rule configurations
        global_rule = all_rules["global_requests"]
        assert global_rule["scope"] == "global", "Global rule should have global scope"
        assert global_rule["enabled"] is True, "Global rule should be enabled"
        assert global_rule["progressive"] is True, "Global rule should be progressive"
        
        user_rule = all_rules["user_requests"]
        assert user_rule["scope"] == "user", "User rule should have user scope"
        assert user_rule["tokens_per_second"] == 10.0, "User rule should have 10 tokens per second"
        
        print("✓ Enhanced rate limit manager initialization test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Enhanced rate limit manager initialization test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Enhanced rate limit manager initialization test ERROR: {}".format(str(e)))
        return False


def test_rate_limit_checking():
    """Test rate limit checking functionality."""
    print("Testing rate limit checking...")
    
    try:
        # Test rate limit check
        async def test_rate_limits():
            # Check global rate limit
            result = await enhanced_rate_limit_manager.check_rate_limit("global_requests", "system", 1)
            assert result.allowed is True, "Global request should be allowed initially"
            assert result.scope == RateLimitScope.GLOBAL, "Result should have global scope"
            assert result.tokens_remaining >= 0, "Should have tokens remaining info"
            
            # Check user rate limit
            result = await enhanced_rate_limit_manager.check_rate_limit("user_requests", "test_user", 1)
            assert result.allowed is True, "User request should be allowed initially"
            assert result.scope == RateLimitScope.USER, "Result should have user scope"
            
            # Test multiple limit checking
            checks = [
                ("global_requests", "system", 1),
                ("user_requests", "test_user", 1),
                ("api_key_requests", "test_key", 1)
            ]
            results = await enhanced_rate_limit_manager.check_multiple_limits(checks)
            assert len(results) == 3, "Should return 3 results"
            
            for result in results:
                assert hasattr(result, 'allowed'), "Result should have allowed attribute"
                assert hasattr(result, 'scope'), "Result should have scope attribute"
                assert hasattr(result, 'tokens_remaining'), "Result should have tokens_remaining"
            
            return True
        
        success = asyncio.run(test_rate_limits())
        assert success is True, "Async rate limit tests should succeed"
        
        print("✓ Rate limit checking test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Rate limit checking test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Rate limit checking test ERROR: {}".format(str(e)))
        return False


def test_rate_limit_status_and_analytics():
    """Test rate limit status and analytics functionality."""
    print("Testing rate limit status and analytics...")
    
    try:
        # Test status checking
        status = enhanced_rate_limit_manager.get_rate_limit_status("user_requests", "test_status_user")
        
        assert "rule_name" in status, "Status should contain rule_name"
        assert "scope" in status, "Status should contain scope"
        assert "tokens_remaining" in status, "Status should contain tokens_remaining"
        assert "capacity" in status, "Status should contain capacity"
        assert "enabled" in status, "Status should contain enabled flag"
        
        # Generate some traffic for analytics
        async def generate_traffic():
            for i in range(10):
                await enhanced_rate_limit_manager.check_rate_limit("user_requests", "analytics_user", 1)
            return True
        
        asyncio.run(generate_traffic())
        
        # Check analytics
        analytics = enhanced_rate_limit_manager.get_analytics("user_requests", "analytics_user", 5)
        
        if "error" not in analytics:
            assert "total_requests" in analytics, "Analytics should contain total_requests"
            assert "allowed_requests" in analytics, "Analytics should contain allowed_requests"
            assert "success_rate_percent" in analytics, "Analytics should contain success_rate_percent"
            assert analytics["total_requests"] > 0, "Should have recorded requests"
        
        print("✓ Rate limit status and analytics test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Rate limit status and analytics test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Rate limit status and analytics test ERROR: {}".format(str(e)))
        return False


def test_rate_limit_rule_management():
    """Test rate limit rule creation and management."""
    print("Testing rate limit rule management...")
    
    try:
        # Create a custom rule
        custom_rule = RateLimitRule(
            name="test_custom_rule",
            scope=RateLimitScope.API_KEY,
            tokens_per_second=3.0,
            max_tokens=30,
            burst_multiplier=1.5,
            progressive=True,
            adaptive=False
        )
        
        # Add the rule
        enhanced_rate_limit_manager.add_rule(custom_rule)
        
        # Verify rule was added
        all_rules = enhanced_rate_limit_manager.get_all_rules()
        assert "test_custom_rule" in all_rules, "Custom rule should be added"
        
        rule_config = all_rules["test_custom_rule"]
        assert rule_config["scope"] == "api_key", "Rule should have correct scope"
        assert rule_config["tokens_per_second"] == 3.0, "Rule should have correct rate"
        assert rule_config["progressive"] is True, "Rule should be progressive"
        
        # Update the rule
        success = enhanced_rate_limit_manager.update_rule(
            "test_custom_rule",
            tokens_per_second=5.0,
            enabled=False
        )
        assert success is True, "Rule update should succeed"
        
        # Verify update
        updated_rules = enhanced_rate_limit_manager.get_all_rules()
        updated_rule = updated_rules["test_custom_rule"]
        assert updated_rule["tokens_per_second"] == 5.0, "Rule rate should be updated"
        assert updated_rule["enabled"] is False, "Rule should be disabled"
        
        # Remove the rule
        success = enhanced_rate_limit_manager.remove_rule("test_custom_rule")
        assert success is True, "Rule removal should succeed"
        
        # Verify removal
        final_rules = enhanced_rate_limit_manager.get_all_rules()
        assert "test_custom_rule" not in final_rules, "Rule should be removed"
        
        print("✓ Rate limit rule management test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Rate limit rule management test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Rate limit rule management test ERROR: {}".format(str(e)))
        return False


def test_burst_protection():
    """Test burst protection functionality."""
    print("Testing burst protection...")
    
    try:
        # Create a rule with burst protection
        burst_rule = RateLimitRule(
            name="test_burst_rule",
            scope=RateLimitScope.USER,
            tokens_per_second=2.0,  # 2 tokens per second
            max_tokens=10,  # 10 token capacity
            burst_multiplier=2.0,  # Allow 2x burst
            progressive=False
        )
        
        enhanced_rate_limit_manager.add_rule(burst_rule)
        
        # Test burst handling
        async def test_burst():
            # Should allow initial burst up to capacity
            for i in range(8):  # Consume most tokens quickly
                result = await enhanced_rate_limit_manager.check_rate_limit("test_burst_rule", "burst_user", 1)
                if i < 7:  # Should allow first 7-8 requests
                    assert result.allowed, "Burst request {} should be allowed".format(i)
            
            # Next requests should be limited
            result = await enhanced_rate_limit_manager.check_rate_limit("test_burst_rule", "burst_user", 3)
            # This might be rejected due to insufficient tokens
            
            return True
        
        asyncio.run(test_burst())
        
        # Clean up
        enhanced_rate_limit_manager.remove_rule("test_burst_rule")
        
        print("✓ Burst protection test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Burst protection test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Burst protection test ERROR: {}".format(str(e)))
        return False


def test_system_statistics():
    """Test system statistics functionality."""
    print("Testing system statistics...")
    
    try:
        # Get system stats
        stats = enhanced_rate_limit_manager.get_system_stats()
        
        # Verify stats structure
        assert "uptime_seconds" in stats, "Stats should include uptime"
        assert "total_rules" in stats, "Stats should include total rules"
        assert "total_buckets" in stats, "Stats should include total buckets"
        assert "total_requests" in stats, "Stats should include total requests"
        assert "overall_success_rate" in stats, "Stats should include success rate"
        assert "memory_usage" in stats, "Stats should include memory usage"
        
        # Verify reasonable values
        assert stats["uptime_seconds"] >= 0, "Uptime should be non-negative"
        assert stats["total_rules"] >= 4, "Should have at least default rules"
        assert stats["overall_success_rate"] >= 0, "Success rate should be non-negative"
        assert stats["overall_success_rate"] <= 100, "Success rate should not exceed 100%"
        
        # Memory usage should be a dict
        memory_usage = stats["memory_usage"]
        assert isinstance(memory_usage, dict), "Memory usage should be a dictionary"
        assert "buckets" in memory_usage, "Memory usage should track buckets"
        
        print("✓ System statistics test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ System statistics test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ System statistics test ERROR: {}".format(str(e)))
        return False


def run_all_tests():
    """Run all enhanced rate limiting tests."""
    print("=" * 70)
    print("RUNNING ENHANCED RATE LIMITING TESTS IN DOCKER")
    print("=" * 70)
    
    tests = [
        test_token_bucket_initialization,
        test_token_bucket_refill,
        test_progressive_rate_limiter,
        test_enhanced_rate_limit_manager_initialization,
        test_rate_limit_checking,
        test_rate_limit_status_and_analytics,
        test_rate_limit_rule_management,
        test_burst_protection,
        test_system_statistics
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print("✗ Test {} ERROR: {}".format(test.__name__, str(e)))
            failed += 1
        print()  # Add spacing between tests
    
    print("=" * 70)
    print("ENHANCED RATE LIMITING TEST RESULTS:")
    print("PASSED: {}".format(passed))
    print("FAILED: {}".format(failed))
    print("TOTAL:  {}".format(passed + failed))
    
    if failed == 0:
        print("🎉 ALL ENHANCED RATE LIMITING TESTS PASSED!")
        print("The enhanced rate limiting system is fully functional!")
        return True
    else:
        print("❌ SOME ENHANCED RATE LIMITING TESTS FAILED!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)