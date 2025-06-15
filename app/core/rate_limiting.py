"""
Advanced Rate Limiting System for API Keys

Implements multiple rate limiting algorithms including sliding window,
fixed window, and token bucket with Redis backend for distributed systems.
"""
import time
import json
import asyncio
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..models.api_key import APIKey, RateLimitType


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    SLIDING_LOG = "sliding_log"


class RateLimitResponse(str, Enum):
    """Rate limit response types."""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    response: RateLimitResponse
    limit: int
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    window_size: Optional[int] = None
    algorithm: Optional[str] = None
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_time.timestamp())),
        }
        
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
        
        if self.window_size:
            headers["X-RateLimit-Window"] = str(self.window_size)
        
        if self.algorithm:
            headers["X-RateLimit-Algorithm"] = self.algorithm
        
        return headers


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    @abstractmethod
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        cost: int = 1
    ) -> RateLimitResult:
        """Check if request is within rate limits."""
        pass
    
    @abstractmethod
    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for a key."""
        pass


class MemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for development/testing."""
    
    def __init__(self, algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW):
        self.algorithm = algorithm
        self.storage: Dict[str, Any] = {}
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    async def _cleanup_expired(self):
        """Clean up expired entries."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        expired_keys = []
        for key, data in self.storage.items():
            if "expires" in data and data["expires"] < current_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.storage[key]
        
        self._last_cleanup = current_time
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        cost: int = 1
    ) -> RateLimitResult:
        """Check rate limit using specified algorithm."""
        await self._cleanup_expired()
        
        if self.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return await self._fixed_window(key, limit, window_seconds, cost)
        elif self.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return await self._sliding_window(key, limit, window_seconds, cost)
        elif self.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return await self._token_bucket(key, limit, window_seconds, cost)
        elif self.algorithm == RateLimitAlgorithm.SLIDING_LOG:
            return await self._sliding_log(key, limit, window_seconds, cost)
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
    
    async def _fixed_window(self, key: str, limit: int, window_seconds: int, cost: int) -> RateLimitResult:
        """Fixed window rate limiting."""
        current_time = time.time()
        window_start = int(current_time // window_seconds) * window_seconds
        window_key = f"{key}:{window_start}"
        
        if window_key not in self.storage:
            self.storage[window_key] = {
                "count": 0,
                "expires": window_start + window_seconds
            }
        
        data = self.storage[window_key]
        new_count = data["count"] + cost
        
        if new_count > limit:
            reset_time = datetime.fromtimestamp(window_start + window_seconds)
            retry_after = int(window_start + window_seconds - current_time)
            
            return RateLimitResult(
                allowed=False,
                response=RateLimitResponse.DENY,
                limit=limit,
                remaining=max(0, limit - data["count"]),
                reset_time=reset_time,
                retry_after=retry_after,
                window_size=window_seconds,
                algorithm=self.algorithm.value
            )
        
        data["count"] = new_count
        reset_time = datetime.fromtimestamp(window_start + window_seconds)
        
        return RateLimitResult(
            allowed=True,
            response=RateLimitResponse.ALLOW,
            limit=limit,
            remaining=limit - new_count,
            reset_time=reset_time,
            window_size=window_seconds,
            algorithm=self.algorithm.value
        )
    
    async def _sliding_window(self, key: str, limit: int, window_seconds: int, cost: int) -> RateLimitResult:
        """Sliding window rate limiting."""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        if key not in self.storage:
            self.storage[key] = {"requests": []}
        
        data = self.storage[key]
        
        # Remove old requests
        data["requests"] = [
            req_time for req_time in data["requests"] 
            if req_time > window_start
        ]
        
        current_count = len(data["requests"])
        
        if current_count + cost > limit:
            # Find the oldest request to determine reset time
            oldest_request = min(data["requests"]) if data["requests"] else current_time
            reset_time = datetime.fromtimestamp(oldest_request + window_seconds)
            retry_after = max(1, int(oldest_request + window_seconds - current_time))
            
            return RateLimitResult(
                allowed=False,
                response=RateLimitResponse.DENY,
                limit=limit,
                remaining=max(0, limit - current_count),
                reset_time=reset_time,
                retry_after=retry_after,
                window_size=window_seconds,
                algorithm=self.algorithm.value
            )
        
        # Add current request
        for _ in range(cost):
            data["requests"].append(current_time)
        
        # Calculate reset time (when oldest request expires)
        oldest_request = min(data["requests"]) if data["requests"] else current_time
        reset_time = datetime.fromtimestamp(oldest_request + window_seconds)
        
        return RateLimitResult(
            allowed=True,
            response=RateLimitResponse.ALLOW,
            limit=limit,
            remaining=limit - (current_count + cost),
            reset_time=reset_time,
            window_size=window_seconds,
            algorithm=self.algorithm.value
        )
    
    async def _token_bucket(self, key: str, limit: int, window_seconds: int, cost: int) -> RateLimitResult:
        """Token bucket rate limiting."""
        current_time = time.time()
        refill_rate = limit / window_seconds  # tokens per second
        
        if key not in self.storage:
            self.storage[key] = {
                "tokens": limit,
                "last_refill": current_time
            }
        
        data = self.storage[key]
        
        # Refill tokens
        time_passed = current_time - data["last_refill"]
        tokens_to_add = time_passed * refill_rate
        data["tokens"] = min(limit, data["tokens"] + tokens_to_add)
        data["last_refill"] = current_time
        
        if data["tokens"] < cost:
            # Calculate when enough tokens will be available
            tokens_needed = cost - data["tokens"]
            time_to_wait = tokens_needed / refill_rate
            reset_time = datetime.fromtimestamp(current_time + time_to_wait)
            
            return RateLimitResult(
                allowed=False,
                response=RateLimitResponse.DENY,
                limit=limit,
                remaining=int(data["tokens"]),
                reset_time=reset_time,
                retry_after=int(time_to_wait) + 1,
                algorithm=self.algorithm.value
            )
        
        data["tokens"] -= cost
        
        # Reset time is when bucket will be full again
        time_to_full = (limit - data["tokens"]) / refill_rate
        reset_time = datetime.fromtimestamp(current_time + time_to_full)
        
        return RateLimitResult(
            allowed=True,
            response=RateLimitResponse.ALLOW,
            limit=limit,
            remaining=int(data["tokens"]),
            reset_time=reset_time,
            algorithm=self.algorithm.value
        )
    
    async def _sliding_log(self, key: str, limit: int, window_seconds: int, cost: int) -> RateLimitResult:
        """Sliding log rate limiting (precise but memory intensive)."""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        if key not in self.storage:
            self.storage[key] = {"log": []}
        
        data = self.storage[key]
        
        # Remove old entries
        data["log"] = [
            entry for entry in data["log"] 
            if entry["time"] > window_start
        ]
        
        # Calculate current usage
        current_usage = sum(entry["cost"] for entry in data["log"])
        
        if current_usage + cost > limit:
            # Find when the oldest entry expires
            if data["log"]:
                oldest_entry = min(data["log"], key=lambda x: x["time"])
                reset_time = datetime.fromtimestamp(oldest_entry["time"] + window_seconds)
                retry_after = max(1, int(oldest_entry["time"] + window_seconds - current_time))
            else:
                reset_time = datetime.fromtimestamp(current_time + window_seconds)
                retry_after = window_seconds
            
            return RateLimitResult(
                allowed=False,
                response=RateLimitResponse.DENY,
                limit=limit,
                remaining=max(0, limit - current_usage),
                reset_time=reset_time,
                retry_after=retry_after,
                window_size=window_seconds,
                algorithm=self.algorithm.value
            )
        
        # Add current request to log
        data["log"].append({
            "time": current_time,
            "cost": cost
        })
        
        # Calculate reset time
        if data["log"]:
            oldest_entry = min(data["log"], key=lambda x: x["time"])
            reset_time = datetime.fromtimestamp(oldest_entry["time"] + window_seconds)
        else:
            reset_time = datetime.fromtimestamp(current_time + window_seconds)
        
        return RateLimitResult(
            allowed=True,
            response=RateLimitResponse.ALLOW,
            limit=limit,
            remaining=limit - (current_usage + cost),
            reset_time=reset_time,
            window_size=window_seconds,
            algorithm=self.algorithm.value
        )
    
    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for a key."""
        if key in self.storage:
            del self.storage[key]
            return True
        return False


class RedisRateLimiter(RateLimiter):
    """Redis-backed rate limiter for production use."""
    
    def __init__(self, redis_client, algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW):
        self.redis = redis_client
        self.algorithm = algorithm
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        cost: int = 1
    ) -> RateLimitResult:
        """Check rate limit using Redis backend."""
        if self.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return await self._redis_fixed_window(key, limit, window_seconds, cost)
        elif self.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return await self._redis_sliding_window(key, limit, window_seconds, cost)
        elif self.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return await self._redis_token_bucket(key, limit, window_seconds, cost)
        else:
            # Fallback to memory implementation for unsupported algorithms
            memory_limiter = MemoryRateLimiter(self.algorithm)
            return await memory_limiter.check_rate_limit(key, limit, window_seconds, cost)
    
    async def _redis_fixed_window(self, key: str, limit: int, window_seconds: int, cost: int) -> RateLimitResult:
        """Redis-based fixed window rate limiting."""
        current_time = time.time()
        window_start = int(current_time // window_seconds) * window_seconds
        redis_key = f"rate_limit:{key}:{window_start}"
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        pipe.get(redis_key)
        pipe.expire(redis_key, window_seconds)
        results = await pipe.execute()
        
        current_count = int(results[0]) if results[0] else 0
        
        if current_count + cost > limit:
            reset_time = datetime.fromtimestamp(window_start + window_seconds)
            retry_after = int(window_start + window_seconds - current_time)
            
            return RateLimitResult(
                allowed=False,
                response=RateLimitResponse.DENY,
                limit=limit,
                remaining=max(0, limit - current_count),
                reset_time=reset_time,
                retry_after=retry_after,
                window_size=window_seconds,
                algorithm=self.algorithm.value
            )
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incrby(redis_key, cost)
        pipe.expire(redis_key, window_seconds)
        await pipe.execute()
        
        reset_time = datetime.fromtimestamp(window_start + window_seconds)
        
        return RateLimitResult(
            allowed=True,
            response=RateLimitResponse.ALLOW,
            limit=limit,
            remaining=limit - (current_count + cost),
            reset_time=reset_time,
            window_size=window_seconds,
            algorithm=self.algorithm.value
        )
    
    async def _redis_sliding_window(self, key: str, limit: int, window_seconds: int, cost: int) -> RateLimitResult:
        """Redis-based sliding window using sorted sets."""
        current_time = time.time()
        window_start = current_time - window_seconds
        redis_key = f"rate_limit:sliding:{key}"
        
        # Clean old entries and count current requests
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_seconds + 1)
        results = await pipe.execute()
        
        current_count = results[1]
        
        if current_count + cost > limit:
            # Get the oldest request time for reset calculation
            oldest_requests = await self.redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest_requests:
                oldest_time = oldest_requests[0][1]
                reset_time = datetime.fromtimestamp(oldest_time + window_seconds)
                retry_after = max(1, int(oldest_time + window_seconds - current_time))
            else:
                reset_time = datetime.fromtimestamp(current_time + window_seconds)
                retry_after = window_seconds
            
            return RateLimitResult(
                allowed=False,
                response=RateLimitResponse.DENY,
                limit=limit,
                remaining=max(0, limit - current_count),
                reset_time=reset_time,
                retry_after=retry_after,
                window_size=window_seconds,
                algorithm=self.algorithm.value
            )
        
        # Add current requests
        pipe = self.redis.pipeline()
        for i in range(cost):
            pipe.zadd(redis_key, {f"{current_time}:{i}": current_time})
        pipe.expire(redis_key, window_seconds + 1)
        await pipe.execute()
        
        # Calculate reset time
        oldest_requests = await self.redis.zrange(redis_key, 0, 0, withscores=True)
        if oldest_requests:
            oldest_time = oldest_requests[0][1]
            reset_time = datetime.fromtimestamp(oldest_time + window_seconds)
        else:
            reset_time = datetime.fromtimestamp(current_time + window_seconds)
        
        return RateLimitResult(
            allowed=True,
            response=RateLimitResponse.ALLOW,
            limit=limit,
            remaining=limit - (current_count + cost),
            reset_time=reset_time,
            window_size=window_seconds,
            algorithm=self.algorithm.value
        )
    
    async def _redis_token_bucket(self, key: str, limit: int, window_seconds: int, cost: int) -> RateLimitResult:
        """Redis-based token bucket implementation."""
        current_time = time.time()
        redis_key = f"rate_limit:bucket:{key}"
        refill_rate = limit / window_seconds
        
        # Lua script for atomic token bucket operations
        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local cost = tonumber(ARGV[2])
        local refill_rate = tonumber(ARGV[3])
        local current_time = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or limit
        local last_refill = tonumber(bucket[2]) or current_time
        
        -- Refill tokens
        local time_passed = current_time - last_refill
        local tokens_to_add = time_passed * refill_rate
        tokens = math.min(limit, tokens + tokens_to_add)
        
        if tokens < cost then
            -- Not enough tokens
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
            redis.call('EXPIRE', key, 3600)  -- 1 hour expiry
            return {0, tokens}
        else
            -- Consume tokens
            tokens = tokens - cost
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
            redis.call('EXPIRE', key, 3600)
            return {1, tokens}
        end
        """
        
        result = await self.redis.eval(
            lua_script, 1, redis_key, 
            limit, cost, refill_rate, current_time
        )
        
        allowed = bool(result[0])
        remaining_tokens = result[1]
        
        if not allowed:
            tokens_needed = cost - remaining_tokens
            time_to_wait = tokens_needed / refill_rate
            reset_time = datetime.fromtimestamp(current_time + time_to_wait)
            
            return RateLimitResult(
                allowed=False,
                response=RateLimitResponse.DENY,
                limit=limit,
                remaining=int(remaining_tokens),
                reset_time=reset_time,
                retry_after=int(time_to_wait) + 1,
                algorithm=self.algorithm.value
            )
        
        # Calculate when bucket will be full
        time_to_full = (limit - remaining_tokens) / refill_rate
        reset_time = datetime.fromtimestamp(current_time + time_to_full)
        
        return RateLimitResult(
            allowed=True,
            response=RateLimitResponse.ALLOW,
            limit=limit,
            remaining=int(remaining_tokens),
            reset_time=reset_time,
            algorithm=self.algorithm.value
        )
    
    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for a key."""
        patterns = [
            f"rate_limit:{key}:*",
            f"rate_limit:sliding:{key}",
            f"rate_limit:bucket:{key}"
        ]
        
        deleted = 0
        for pattern in patterns:
            keys = await self.redis.keys(pattern)
            if keys:
                deleted += await self.redis.delete(*keys)
        
        return deleted > 0


class APIKeyRateLimitManager:
    """High-level rate limit manager for API keys."""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    def _get_window_seconds(self, rate_limit_type: RateLimitType) -> int:
        """Convert rate limit type to seconds."""
        mapping = {
            RateLimitType.requests_per_minute: 60,
            RateLimitType.requests_per_hour: 3600,
            RateLimitType.requests_per_day: 86400,
            RateLimitType.requests_per_month: 2592000  # 30 days
        }
        return mapping.get(rate_limit_type, 3600)  # Default to 1 hour
    
    async def check_api_key_rate_limit(
        self, 
        api_key: APIKey, 
        cost: int = 1,
        endpoint: Optional[str] = None
    ) -> RateLimitResult:
        """
        Check rate limit for an API key.
        
        Args:
            api_key: API key object
            cost: Request cost (default 1)
            endpoint: Optional endpoint-specific limiting
            
        Returns:
            RateLimitResult with decision and metadata
        """
        if not api_key.rate_limit:
            # No rate limit configured
            return RateLimitResult(
                allowed=True,
                response=RateLimitResponse.ALLOW,
                limit=float('inf'),
                remaining=float('inf'),
                reset_time=datetime.fromtimestamp(time.time() + 3600),
                algorithm="none"
            )
        
        # Create rate limit key
        key_parts = [str(api_key.id)]
        if endpoint:
            # Endpoint-specific rate limiting
            key_parts.append(endpoint)
        
        rate_limit_key = ":".join(key_parts)
        window_seconds = self._get_window_seconds(api_key.rate_limit_period)
        
        return await self.rate_limiter.check_rate_limit(
            rate_limit_key,
            api_key.rate_limit,
            window_seconds,
            cost
        )
    
    async def check_global_rate_limit(
        self, 
        user_id: str, 
        limit: int, 
        window_seconds: int,
        cost: int = 1
    ) -> RateLimitResult:
        """Check global rate limit for a user across all API keys."""
        key = f"user:{user_id}:global"
        return await self.rate_limiter.check_rate_limit(
            key, limit, window_seconds, cost
        )
    
    async def check_endpoint_rate_limit(
        self, 
        endpoint: str, 
        limit: int, 
        window_seconds: int,
        cost: int = 1
    ) -> RateLimitResult:
        """Check global rate limit for a specific endpoint."""
        key = f"endpoint:{endpoint}"
        return await self.rate_limiter.check_rate_limit(
            key, limit, window_seconds, cost
        )
    
    async def reset_api_key_rate_limit(self, api_key: APIKey) -> bool:
        """Reset rate limit for an API key."""
        key = str(api_key.id)
        return await self.rate_limiter.reset_rate_limit(key)
    
    async def get_rate_limit_status(self, api_key: APIKey) -> Dict[str, Any]:
        """Get current rate limit status for an API key."""
        # This would typically check current usage without incrementing
        result = await self.check_api_key_rate_limit(api_key, cost=0)
        
        return {
            "api_key_id": api_key.key_id,
            "rate_limit": api_key.rate_limit,
            "rate_limit_period": api_key.rate_limit_period.value,
            "current_usage": api_key.rate_limit - result.remaining if result.remaining != float('inf') else 0,
            "remaining": result.remaining,
            "reset_time": result.reset_time.isoformat(),
            "algorithm": result.algorithm
        }