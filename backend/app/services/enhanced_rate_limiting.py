"""
Enhanced Rate Limiting Service with Token Bucket Algorithm.

This service provides advanced rate limiting capabilities including:
- Token bucket algorithm for burst handling
- Progressive rate limiting with dynamic adjustments
- Per-user, per-API-key, and global rate limiting
- Adaptive limits based on usage patterns
- Rate limit analytics and monitoring
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from collections import defaultdict, deque

from ..core.config import settings


class RateLimitScope(str, Enum):
    """Rate limit scopes."""
    GLOBAL = "global"
    USER = "user"
    API_KEY = "api_key"
    IP_ADDRESS = "ip"
    ENDPOINT = "endpoint"


class RateLimitAction(str, Enum):
    """Actions to take when rate limit is exceeded."""
    REJECT = "reject"
    DELAY = "delay"
    THROTTLE = "throttle"
    WARN = "warn"


@dataclass
class RateLimitRule:
    """Configuration for a rate limit rule."""
    name: str
    scope: RateLimitScope
    tokens_per_second: float  # Token refill rate
    max_tokens: int  # Bucket capacity
    burst_multiplier: float = 2.0  # Allow bursts up to this multiplier
    window_size: int = 60  # Window size in seconds for analytics
    action: RateLimitAction = RateLimitAction.REJECT
    enabled: bool = True
    progressive: bool = False  # Enable progressive rate limiting
    adaptive: bool = False  # Enable adaptive rate limiting
    penalty_factor: float = 0.5  # Reduction factor for violations
    recovery_factor: float = 1.1  # Recovery factor for good behavior
    min_limit: float = 0.1  # Minimum allowed rate
    max_limit: float = 100.0  # Maximum allowed rate


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float
    total_requests: int = 0
    rejected_requests: int = 0
    burst_allowance: int = 0
    
    def __post_init__(self):
        if self.last_refill == 0:
            self.last_refill = time.time()
    
    def refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > 0:
            # Add tokens based on refill rate
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens."""
        self.refill()
        self.total_requests += 1
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        else:
            self.rejected_requests += 1
            return False
    
    def peek(self) -> float:
        """Check available tokens without consuming."""
        self.refill()
        return self.tokens
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bucket statistics."""
        total = max(self.total_requests, 1)
        return {
            "capacity": self.capacity,
            "available_tokens": self.tokens,
            "refill_rate": self.refill_rate,
            "total_requests": self.total_requests,
            "rejected_requests": self.rejected_requests,
            "success_rate": ((total - self.rejected_requests) / total) * 100,
            "utilization": ((self.capacity - self.tokens) / self.capacity) * 100
        }


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    scope: RateLimitScope
    rule_name: str
    tokens_remaining: float
    reset_time: float
    retry_after: Optional[float] = None
    current_rate: Optional[float] = None
    reason: Optional[str] = None


class ProgressiveRateLimiter:
    """Progressive rate limiter that adjusts limits based on behavior."""
    
    def __init__(self, base_rule: RateLimitRule):
        self.base_rule = base_rule
        self.violation_history: deque = deque(maxlen=100)
        self.current_multiplier = 1.0
        self.last_adjustment = time.time()
    
    def record_violation(self):
        """Record a rate limit violation."""
        now = time.time()
        self.violation_history.append(now)
        
        # Adjust rate limit downward
        recent_violations = sum(1 for t in self.violation_history if now - t < 300)  # 5 minutes
        if recent_violations >= 3:
            self.current_multiplier *= self.base_rule.penalty_factor
            self.current_multiplier = max(self.current_multiplier, self.base_rule.min_limit)
            self.last_adjustment = now
    
    def record_success(self):
        """Record successful usage (no violation)."""
        now = time.time()
        
        # Gradually recover rate limit if no recent violations
        recent_violations = sum(1 for t in self.violation_history if now - t < 600)  # 10 minutes
        if recent_violations == 0 and now - self.last_adjustment > 300:  # 5 minutes since last adjustment
            self.current_multiplier *= self.base_rule.recovery_factor
            self.current_multiplier = min(self.current_multiplier, self.base_rule.max_limit)
            self.last_adjustment = now
    
    def get_current_rate(self) -> float:
        """Get current adjusted rate."""
        return self.base_rule.tokens_per_second * self.current_multiplier


class EnhancedRateLimitManager:
    """Enhanced rate limiting manager with token bucket algorithm."""
    
    def __init__(self):
        self.rules: Dict[str, RateLimitRule] = {}
        self.buckets: Dict[str, TokenBucket] = {}
        self.progressive_limiters: Dict[str, ProgressiveRateLimiter] = {}
        self.analytics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.startup_time = time.time()
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default rate limiting rules."""
        default_rules = [
            RateLimitRule(
                name="global_requests",
                scope=RateLimitScope.GLOBAL,
                tokens_per_second=100.0,
                max_tokens=1000,
                burst_multiplier=2.0,
                progressive=True,
                adaptive=True
            ),
            RateLimitRule(
                name="user_requests",
                scope=RateLimitScope.USER,
                tokens_per_second=10.0,
                max_tokens=100,
                burst_multiplier=1.5,
                progressive=True,
                adaptive=True
            ),
            RateLimitRule(
                name="api_key_requests",
                scope=RateLimitScope.API_KEY,
                tokens_per_second=5.0,
                max_tokens=50,
                burst_multiplier=2.0,
                progressive=True,
                adaptive=True
            ),
            RateLimitRule(
                name="ip_requests",
                scope=RateLimitScope.IP_ADDRESS,
                tokens_per_second=20.0,
                max_tokens=200,
                burst_multiplier=1.5,
                progressive=False,
                adaptive=False
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: RateLimitRule):
        """Add a rate limiting rule."""
        self.rules[rule.name] = rule
        print(f"Added rate limit rule: {rule.name} ({rule.scope.value})")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rate limiting rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            # Clean up associated buckets and limiters
            to_remove = [key for key in self.buckets.keys() if key.startswith(f"{rule_name}:")]
            for key in to_remove:
                del self.buckets[key]
            
            to_remove = [key for key in self.progressive_limiters.keys() if key.startswith(f"{rule_name}:")]
            for key in to_remove:
                del self.progressive_limiters[key]
            
            return True
        return False
    
    def _get_bucket_key(self, rule_name: str, identifier: str) -> str:
        """Generate bucket key for a rule and identifier."""
        return f"{rule_name}:{identifier}"
    
    def _get_or_create_bucket(self, rule: RateLimitRule, identifier: str) -> TokenBucket:
        """Get or create a token bucket for the given rule and identifier."""
        bucket_key = self._get_bucket_key(rule.name, identifier)
        
        if bucket_key not in self.buckets:
            # Determine effective rate
            effective_rate = rule.tokens_per_second
            if rule.progressive:
                progressive_limiter = self._get_or_create_progressive_limiter(rule, identifier)
                effective_rate = progressive_limiter.get_current_rate()
            
            self.buckets[bucket_key] = TokenBucket(
                capacity=rule.max_tokens,
                tokens=rule.max_tokens,  # Start with full bucket
                refill_rate=effective_rate,
                last_refill=time.time()
            )
        
        return self.buckets[bucket_key]
    
    def _get_or_create_progressive_limiter(self, rule: RateLimitRule, identifier: str) -> ProgressiveRateLimiter:
        """Get or create a progressive rate limiter."""
        limiter_key = self._get_bucket_key(rule.name, identifier)
        
        if limiter_key not in self.progressive_limiters:
            self.progressive_limiters[limiter_key] = ProgressiveRateLimiter(rule)
        
        return self.progressive_limiters[limiter_key]
    
    async def check_rate_limit(
        self,
        rule_name: str,
        identifier: str,
        tokens: int = 1
    ) -> RateLimitResult:
        """Check if a request is within rate limits."""
        if rule_name not in self.rules:
            return RateLimitResult(
                allowed=True,
                scope=RateLimitScope.GLOBAL,
                rule_name=rule_name,
                tokens_remaining=float('inf'),
                reset_time=0,
                reason="Rule not found"
            )
        
        rule = self.rules[rule_name]
        if not rule.enabled:
            return RateLimitResult(
                allowed=True,
                scope=rule.scope,
                rule_name=rule_name,
                tokens_remaining=float('inf'),
                reset_time=0,
                reason="Rule disabled"
            )
        
        bucket = self._get_or_create_bucket(rule, identifier)
        allowed = bucket.consume(tokens)
        
        # Record analytics
        self._record_analytics(rule_name, identifier, allowed, bucket)
        
        # Handle progressive rate limiting
        if rule.progressive:
            progressive_limiter = self._get_or_create_progressive_limiter(rule, identifier)
            if allowed:
                progressive_limiter.record_success()
            else:
                progressive_limiter.record_violation()
                # Update bucket refill rate
                bucket.refill_rate = progressive_limiter.get_current_rate()
        
        # Calculate reset time
        if bucket.tokens < tokens and bucket.refill_rate > 0:
            reset_time = time.time() + ((tokens - bucket.tokens) / bucket.refill_rate)
        else:
            reset_time = time.time() + (rule.max_tokens / rule.tokens_per_second)
        
        return RateLimitResult(
            allowed=allowed,
            scope=rule.scope,
            rule_name=rule_name,
            tokens_remaining=bucket.tokens,
            reset_time=reset_time,
            retry_after=reset_time - time.time() if not allowed else None,
            current_rate=bucket.refill_rate,
            reason="Rate limit exceeded" if not allowed else None
        )
    
    def _record_analytics(self, rule_name: str, identifier: str, allowed: bool, bucket: TokenBucket):
        """Record analytics data for rate limiting."""
        now = time.time()
        analytics_key = f"{rule_name}:{identifier}"
        
        data_point = {
            "timestamp": now,
            "allowed": allowed,
            "tokens_remaining": bucket.tokens,
            "total_requests": bucket.total_requests,
            "rejected_requests": bucket.rejected_requests
        }
        
        self.analytics[analytics_key].append(data_point)
        
        # Keep only recent data (last hour)
        cutoff = now - 3600
        self.analytics[analytics_key] = [
            point for point in self.analytics[analytics_key]
            if point["timestamp"] > cutoff
        ]
    
    async def check_multiple_limits(
        self,
        checks: List[Tuple[str, str, int]]  # [(rule_name, identifier, tokens)]
    ) -> List[RateLimitResult]:
        """Check multiple rate limits in a single call."""
        results = []
        for rule_name, identifier, tokens in checks:
            result = await self.check_rate_limit(rule_name, identifier, tokens)
            results.append(result)
        return results
    
    def get_rate_limit_status(self, rule_name: str, identifier: str) -> Dict[str, Any]:
        """Get current rate limit status without consuming tokens."""
        if rule_name not in self.rules:
            return {"error": "Rule not found"}
        
        rule = self.rules[rule_name]
        bucket_key = self._get_bucket_key(rule_name, identifier)
        
        if bucket_key in self.buckets:
            bucket = self.buckets[bucket_key]
            bucket.refill()  # Update token count
            
            status = {
                "rule_name": rule_name,
                "scope": rule.scope.value,
                "tokens_remaining": bucket.tokens,
                "capacity": bucket.capacity,
                "refill_rate": bucket.refill_rate,
                "utilization_percent": ((bucket.capacity - bucket.tokens) / bucket.capacity) * 100,
                "enabled": rule.enabled
            }
            
            # Add progressive limiter info if applicable
            if rule.progressive and bucket_key in self.progressive_limiters:
                progressive_limiter = self.progressive_limiters[bucket_key]
                status["progressive"] = {
                    "current_multiplier": progressive_limiter.current_multiplier,
                    "current_rate": progressive_limiter.get_current_rate(),
                    "recent_violations": len([
                        v for v in progressive_limiter.violation_history
                        if time.time() - v < 300
                    ])
                }
            
            return status
        else:
            return {
                "rule_name": rule_name,
                "scope": rule.scope.value,
                "tokens_remaining": rule.max_tokens,
                "capacity": rule.max_tokens,
                "refill_rate": rule.tokens_per_second,
                "utilization_percent": 0,
                "enabled": rule.enabled
            }
    
    def get_analytics(self, rule_name: str, identifier: str, window_minutes: int = 60) -> Dict[str, Any]:
        """Get analytics data for a specific rule and identifier."""
        analytics_key = f"{rule_name}:{identifier}"
        
        if analytics_key not in self.analytics:
            return {"error": "No analytics data available"}
        
        # Filter data by time window
        cutoff = time.time() - (window_minutes * 60)
        recent_data = [
            point for point in self.analytics[analytics_key]
            if point["timestamp"] > cutoff
        ]
        
        if not recent_data:
            return {"error": "No recent analytics data"}
        
        # Calculate metrics
        total_requests = len(recent_data)
        allowed_requests = sum(1 for point in recent_data if point["allowed"])
        rejected_requests = total_requests - allowed_requests
        
        success_rate = (allowed_requests / total_requests) * 100 if total_requests > 0 else 0
        
        # Calculate request rate (requests per minute)
        time_span = (recent_data[-1]["timestamp"] - recent_data[0]["timestamp"]) / 60
        request_rate = total_requests / time_span if time_span > 0 else 0
        
        return {
            "rule_name": rule_name,
            "identifier": identifier,
            "window_minutes": window_minutes,
            "total_requests": total_requests,
            "allowed_requests": allowed_requests,
            "rejected_requests": rejected_requests,
            "success_rate_percent": success_rate,
            "requests_per_minute": request_rate,
            "data_points": len(recent_data)
        }
    
    def get_all_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get all rate limiting rules and their configurations."""
        return {
            name: {
                "scope": rule.scope.value,
                "tokens_per_second": rule.tokens_per_second,
                "max_tokens": rule.max_tokens,
                "burst_multiplier": rule.burst_multiplier,
                "action": rule.action.value,
                "enabled": rule.enabled,
                "progressive": rule.progressive,
                "adaptive": rule.adaptive
            }
            for name, rule in self.rules.items()
        }
    
    def update_rule(self, rule_name: str, **kwargs) -> bool:
        """Update an existing rate limiting rule."""
        if rule_name not in self.rules:
            return False
        
        rule = self.rules[rule_name]
        
        # Update rule attributes
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        # Update existing buckets with new parameters
        prefix = f"{rule_name}:"
        for bucket_key in list(self.buckets.keys()):
            if bucket_key.startswith(prefix):
                bucket = self.buckets[bucket_key]
                if "tokens_per_second" in kwargs:
                    bucket.refill_rate = kwargs["tokens_per_second"]
                if "max_tokens" in kwargs:
                    bucket.capacity = kwargs["max_tokens"]
                    bucket.tokens = min(bucket.tokens, bucket.capacity)
        
        return True
    
    def reset_bucket(self, rule_name: str, identifier: str) -> bool:
        """Reset a specific token bucket."""
        bucket_key = self._get_bucket_key(rule_name, identifier)
        
        if bucket_key in self.buckets:
            rule = self.rules.get(rule_name)
            if rule:
                bucket = self.buckets[bucket_key]
                bucket.tokens = rule.max_tokens
                bucket.total_requests = 0
                bucket.rejected_requests = 0
                bucket.last_refill = time.time()
                return True
        
        return False
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        total_buckets = len(self.buckets)
        total_rules = len(self.rules)
        total_progressive_limiters = len(self.progressive_limiters)
        
        # Calculate aggregate stats
        total_requests = sum(bucket.total_requests for bucket in self.buckets.values())
        total_rejected = sum(bucket.rejected_requests for bucket in self.buckets.values())
        
        success_rate = ((total_requests - total_rejected) / total_requests * 100) if total_requests > 0 else 100
        
        return {
            "uptime_seconds": time.time() - self.startup_time,
            "total_rules": total_rules,
            "total_buckets": total_buckets,
            "total_progressive_limiters": total_progressive_limiters,
            "total_requests": total_requests,
            "total_rejected": total_rejected,
            "overall_success_rate": success_rate,
            "memory_usage": {
                "buckets": len(self.buckets),
                "analytics_keys": len(self.analytics),
                "progressive_limiters": len(self.progressive_limiters)
            }
        }


# Global enhanced rate limit manager instance
enhanced_rate_limit_manager = EnhancedRateLimitManager()