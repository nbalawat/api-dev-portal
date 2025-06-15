"""
Tests for Rate Limiting Functionality

Tests various aspects of the rate limiting system including:
- Different rate limiting algorithms
- Rate limit enforcement
- Rate limit headers
- Backend implementations (Redis and memory)
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.core.rate_limiting import (
    RateLimitManager, RateLimitResult, RateLimitResponse,
    RateLimitAlgorithm, RateLimitBackend, MemoryRateLimitBackend,
    FixedWindowRateLimiter, SlidingWindowRateLimiter, TokenBucketRateLimiter
)


class TestRateLimitAlgorithms:
    """Test individual rate limiting algorithms."""
    
    @pytest.mark.asyncio
    async def test_fixed_window_limiter(self):
        """Test fixed window rate limiting."""
        backend = MemoryRateLimitBackend()
        limiter = FixedWindowRateLimiter(backend)
        
        key = "test_key"
        limit = 5
        window_seconds = 60
        
        # Should allow requests within limit
        for i in range(limit):
            result = await limiter.check_rate_limit(key, limit, window_seconds)
            assert result.allowed, f"Request {i+1} should be allowed"
            assert result.remaining == limit - (i + 1), "Remaining count should decrease"
        
        # Should deny request over limit
        result = await limiter.check_rate_limit(key, limit, window_seconds)
        assert not result.allowed, "Request over limit should be denied"
        assert result.remaining == 0, "No requests should remain"
    
    @pytest.mark.asyncio
    async def test_sliding_window_limiter(self):
        """Test sliding window rate limiting."""
        backend = MemoryRateLimitBackend()
        limiter = SlidingWindowRateLimiter(backend)
        
        key = "test_key"
        limit = 3
        window_seconds = 10
        
        # Allow initial requests
        for i in range(limit):
            result = await limiter.check_rate_limit(key, limit, window_seconds)
            assert result.allowed, f"Initial request {i+1} should be allowed"
        
        # Should deny over limit
        result = await limiter.check_rate_limit(key, limit, window_seconds)
        assert not result.allowed, "Request over limit should be denied"
    
    @pytest.mark.asyncio
    async def test_token_bucket_limiter(self):
        """Test token bucket rate limiting."""
        backend = MemoryRateLimitBackend()
        limiter = TokenBucketRateLimiter(backend)
        
        key = "test_key"
        limit = 5
        window_seconds = 60
        
        # Initial requests should be allowed (bucket starts full)
        for i in range(limit):
            result = await limiter.check_rate_limit(key, limit, window_seconds)
            assert result.allowed, f"Initial request {i+1} should be allowed"
        
        # Next request should be denied (bucket empty)
        result = await limiter.check_rate_limit(key, limit, window_seconds)
        assert not result.allowed, "Request on empty bucket should be denied"


class TestRateLimitBackends:
    """Test rate limiting backends."""
    
    @pytest.mark.asyncio
    async def test_memory_backend(self):
        """Test memory-based rate limiting backend."""
        backend = MemoryRateLimitBackend()
        
        # Test increment
        result = await backend.increment("test_key", 60)
        assert result == 1, "First increment should return 1"
        
        result = await backend.increment("test_key", 60)
        assert result == 2, "Second increment should return 2"
        
        # Test get
        value = await backend.get("test_key")
        assert value == 2, "Get should return current value"
        
        # Test expire
        await backend.expire("test_key", 1)  # 1 second
        await asyncio.sleep(1.1)  # Wait for expiration
        
        value = await backend.get("test_key")
        assert value == 0, "Value should be 0 after expiration"
    
    @pytest.mark.asyncio
    async def test_memory_backend_cleanup(self):
        """Test memory backend cleanup functionality."""
        backend = MemoryRateLimitBackend()
        
        # Add some expired entries
        await backend.increment("key1", 1)  # Expires in 1 second
        await backend.increment("key2", 1)
        await backend.increment("key3", 60)  # Doesn't expire soon
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Trigger cleanup
        await backend._cleanup_expired()
        
        # Only key3 should remain
        assert await backend.get("key1") == 0, "Expired key1 should be cleaned up"
        assert await backend.get("key2") == 0, "Expired key2 should be cleaned up"
        assert await backend.get("key3") == 1, "Non-expired key3 should remain"


class TestRateLimitManager:
    """Test the main rate limit manager."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_manager_creation(self):
        """Test rate limit manager creation with different configurations."""
        # Test with memory backend
        manager = RateLimitManager(
            backend_type=RateLimitBackend.MEMORY,
            default_algorithm=RateLimitAlgorithm.FIXED_WINDOW
        )
        
        assert manager.backend is not None, "Backend should be initialized"
        assert manager.default_algorithm == RateLimitAlgorithm.FIXED_WINDOW
    
    @pytest.mark.asyncio
    async def test_check_rate_limit(self):
        """Test rate limit checking through manager."""
        manager = RateLimitManager(
            backend_type=RateLimitBackend.MEMORY,
            default_algorithm=RateLimitAlgorithm.FIXED_WINDOW
        )
        
        api_key_id = "test_api_key"
        limit = 10
        window_seconds = 60
        
        # First request should be allowed
        result = await manager.check_rate_limit(
            api_key_id=api_key_id,
            limit=limit,
            window_seconds=window_seconds
        )
        
        assert result.allowed, "First request should be allowed"
        assert result.limit == limit, "Limit should match"
        assert result.remaining == limit - 1, "Remaining should be decremented"
        assert isinstance(result.reset_time, datetime), "Reset time should be datetime"
    
    @pytest.mark.asyncio
    async def test_different_algorithms(self):
        """Test manager with different algorithms."""
        algorithms = [
            RateLimitAlgorithm.FIXED_WINDOW,
            RateLimitAlgorithm.SLIDING_WINDOW,
            RateLimitAlgorithm.TOKEN_BUCKET
        ]
        
        for algorithm in algorithms:
            manager = RateLimitManager(
                backend_type=RateLimitBackend.MEMORY,
                default_algorithm=algorithm
            )
            
            result = await manager.check_rate_limit(
                api_key_id=f"test_key_{algorithm.value}",
                limit=5,
                window_seconds=60
            )
            
            assert result.allowed, f"Request should be allowed for {algorithm.value}"
            assert result.response.algorithm == algorithm.value
    
    @pytest.mark.asyncio
    async def test_endpoint_specific_limits(self):
        """Test endpoint-specific rate limiting."""
        manager = RateLimitManager(
            backend_type=RateLimitBackend.MEMORY,
            default_algorithm=RateLimitAlgorithm.FIXED_WINDOW
        )
        
        api_key_id = "test_api_key"
        endpoint = "/api/v1/expensive-operation"
        
        # Configure endpoint-specific limit
        await manager.set_endpoint_limit(endpoint, 2, 60)  # Only 2 requests per minute
        
        # First two requests should be allowed
        for i in range(2):
            result = await manager.check_rate_limit(
                api_key_id=api_key_id,
                limit=100,  # High global limit
                window_seconds=60,
                endpoint=endpoint
            )
            assert result.allowed, f"Request {i+1} should be allowed"
        
        # Third request should be denied due to endpoint limit
        result = await manager.check_rate_limit(
            api_key_id=api_key_id,
            limit=100,
            window_seconds=60,
            endpoint=endpoint
        )
        assert not result.allowed, "Third request should be denied by endpoint limit"
    
    @pytest.mark.asyncio
    async def test_global_rate_limits(self):
        """Test global rate limiting across all keys."""
        manager = RateLimitManager(
            backend_type=RateLimitBackend.MEMORY,
            default_algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            global_limit=5,
            global_window_seconds=60
        )
        
        # Use different API keys but hit global limit
        for i in range(5):
            result = await manager.check_rate_limit(
                api_key_id=f"api_key_{i}",
                limit=1000,  # High individual limit
                window_seconds=60
            )
            assert result.allowed, f"Request {i+1} should be allowed"
        
        # Sixth request should be denied by global limit
        result = await manager.check_rate_limit(
            api_key_id="api_key_6",
            limit=1000,
            window_seconds=60
        )
        assert not result.allowed, "Request should be denied by global limit"


class TestRateLimitIntegration:
    """Integration tests for rate limiting with FastAPI."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self):
        """Test that rate limit headers are correctly set."""
        manager = RateLimitManager(
            backend_type=RateLimitBackend.MEMORY,
            default_algorithm=RateLimitAlgorithm.FIXED_WINDOW
        )
        
        result = await manager.check_rate_limit(
            api_key_id="test_key",
            limit=10,
            window_seconds=60
        )
        
        # Check that response contains proper rate limit info
        assert result.response.limit == 10, "Response should contain limit"
        assert result.response.remaining == 9, "Response should contain remaining"
        assert result.response.reset_timestamp is not None, "Response should contain reset time"
        assert result.response.algorithm is not None, "Response should contain algorithm"
    
    @pytest.mark.asyncio
    async def test_burst_handling(self):
        """Test handling of burst requests."""
        manager = RateLimitManager(
            backend_type=RateLimitBackend.MEMORY,
            default_algorithm=RateLimitAlgorithm.TOKEN_BUCKET
        )
        
        api_key_id = "burst_test_key"
        limit = 5
        
        # Send burst of requests
        results = []
        for i in range(10):  # More than limit
            result = await manager.check_rate_limit(
                api_key_id=api_key_id,
                limit=limit,
                window_seconds=60
            )
            results.append(result)
        
        # First 5 should be allowed, rest denied
        allowed_count = sum(1 for r in results if r.allowed)
        denied_count = sum(1 for r in results if not r.allowed)
        
        assert allowed_count == limit, f"Should allow {limit} requests"
        assert denied_count == 5, "Should deny 5 excess requests"
    
    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self):
        """Test rate limit recovery after window expires."""
        manager = RateLimitManager(
            backend_type=RateLimitBackend.MEMORY,
            default_algorithm=RateLimitAlgorithm.FIXED_WINDOW
        )
        
        api_key_id = "recovery_test_key"
        limit = 2
        window_seconds = 1  # Short window for testing
        
        # Exhaust rate limit
        for i in range(limit):
            result = await manager.check_rate_limit(
                api_key_id=api_key_id,
                limit=limit,
                window_seconds=window_seconds
            )
            assert result.allowed, f"Initial request {i+1} should be allowed"
        
        # Next request should be denied
        result = await manager.check_rate_limit(
            api_key_id=api_key_id,
            limit=limit,
            window_seconds=window_seconds
        )
        assert not result.allowed, "Request should be denied when limit exceeded"
        
        # Wait for window to expire
        await asyncio.sleep(window_seconds + 0.1)
        
        # Should be able to make requests again
        result = await manager.check_rate_limit(
            api_key_id=api_key_id,
            limit=limit,
            window_seconds=window_seconds
        )
        assert result.allowed, "Request should be allowed after window expires"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])