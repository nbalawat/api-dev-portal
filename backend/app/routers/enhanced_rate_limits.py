"""
Enhanced Rate Limiting management router for administrative control.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..dependencies.auth import get_admin_user, get_current_active_user
from ..models.user import User
from ..services.enhanced_rate_limiting import (
    enhanced_rate_limit_manager,
    RateLimitRule,
    RateLimitScope,
    RateLimitAction
)


router = APIRouter(prefix="/enhanced-rate-limits")


class RateLimitRuleCreate(BaseModel):
    """Request model for creating rate limit rules."""
    name: str = Field(..., description="Unique name for the rule")
    scope: RateLimitScope = Field(..., description="Scope of the rate limit")
    tokens_per_second: float = Field(..., gt=0, description="Token refill rate per second")
    max_tokens: int = Field(..., gt=0, description="Maximum bucket capacity")
    burst_multiplier: float = Field(2.0, gt=1.0, description="Burst allowance multiplier")
    window_size: int = Field(60, gt=0, description="Analytics window size in seconds")
    action: RateLimitAction = Field(RateLimitAction.REJECT, description="Action when limit exceeded")
    enabled: bool = Field(True, description="Whether the rule is enabled")
    progressive: bool = Field(False, description="Enable progressive rate limiting")
    adaptive: bool = Field(False, description="Enable adaptive rate limiting")
    penalty_factor: float = Field(0.5, gt=0, le=1, description="Rate reduction factor for violations")
    recovery_factor: float = Field(1.1, ge=1, description="Rate recovery factor for good behavior")
    min_limit: float = Field(0.1, gt=0, description="Minimum allowed rate")
    max_limit: float = Field(100.0, gt=0, description="Maximum allowed rate")


class RateLimitRuleUpdate(BaseModel):
    """Request model for updating rate limit rules."""
    tokens_per_second: Optional[float] = Field(None, gt=0)
    max_tokens: Optional[int] = Field(None, gt=0)
    burst_multiplier: Optional[float] = Field(None, gt=1.0)
    enabled: Optional[bool] = None
    progressive: Optional[bool] = None
    adaptive: Optional[bool] = None
    penalty_factor: Optional[float] = Field(None, gt=0, le=1)
    recovery_factor: Optional[float] = Field(None, ge=1)


class RateLimitStatusResponse(BaseModel):
    """Response model for rate limit status."""
    rule_name: str
    scope: str
    tokens_remaining: float
    capacity: int
    refill_rate: float
    utilization_percent: float
    enabled: bool
    progressive: Optional[Dict[str, Any]] = None


class RateLimitAnalyticsResponse(BaseModel):
    """Response model for rate limit analytics."""
    rule_name: str
    identifier: str
    window_minutes: int
    total_requests: int
    allowed_requests: int
    rejected_requests: int
    success_rate_percent: float
    requests_per_minute: float
    data_points: int


@router.get("/rules")
async def get_rate_limit_rules(
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, Dict[str, Any]]:
    """
    Get all rate limiting rules and their configurations.
    
    Admin-only endpoint that returns comprehensive information about
    all configured rate limiting rules.
    """
    return enhanced_rate_limit_manager.get_all_rules()


@router.post("/rules")
async def create_rate_limit_rule(
    rule_data: RateLimitRuleCreate,
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, str]:
    """
    Create a new rate limiting rule.
    
    Admin-only endpoint for creating custom rate limiting rules
    with specific parameters and behavior.
    """
    # Check if rule already exists
    existing_rules = enhanced_rate_limit_manager.get_all_rules()
    if rule_data.name in existing_rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rate limit rule '{rule_data.name}' already exists"
        )
    
    # Create the rule
    rule = RateLimitRule(
        name=rule_data.name,
        scope=rule_data.scope,
        tokens_per_second=rule_data.tokens_per_second,
        max_tokens=rule_data.max_tokens,
        burst_multiplier=rule_data.burst_multiplier,
        window_size=rule_data.window_size,
        action=rule_data.action,
        enabled=rule_data.enabled,
        progressive=rule_data.progressive,
        adaptive=rule_data.adaptive,
        penalty_factor=rule_data.penalty_factor,
        recovery_factor=rule_data.recovery_factor,
        min_limit=rule_data.min_limit,
        max_limit=rule_data.max_limit
    )
    
    enhanced_rate_limit_manager.add_rule(rule)
    
    return {
        "message": f"Rate limit rule '{rule_data.name}' created successfully",
        "rule_name": rule_data.name
    }


@router.put("/rules/{rule_name}")
async def update_rate_limit_rule(
    rule_name: str,
    rule_update: RateLimitRuleUpdate,
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, str]:
    """
    Update an existing rate limiting rule.
    
    Admin-only endpoint for modifying rate limiting rule parameters.
    """
    # Check if rule exists
    existing_rules = enhanced_rate_limit_manager.get_all_rules()
    if rule_name not in existing_rules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit rule '{rule_name}' not found"
        )
    
    # Update the rule
    update_data = rule_update.dict(exclude_unset=True)
    success = enhanced_rate_limit_manager.update_rule(rule_name, **update_data)
    
    if success:
        return {
            "message": f"Rate limit rule '{rule_name}' updated successfully",
            "rule_name": rule_name
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rate limit rule '{rule_name}'"
        )


@router.delete("/rules/{rule_name}")
async def delete_rate_limit_rule(
    rule_name: str,
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, str]:
    """
    Delete a rate limiting rule.
    
    Admin-only endpoint for removing rate limiting rules.
    Warning: This will also remove all associated token buckets and analytics.
    """
    success = enhanced_rate_limit_manager.remove_rule(rule_name)
    
    if success:
        return {
            "message": f"Rate limit rule '{rule_name}' deleted successfully",
            "rule_name": rule_name
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit rule '{rule_name}' not found"
        )


@router.get("/status/{rule_name}/{identifier}", response_model=RateLimitStatusResponse)
async def get_rate_limit_status(
    rule_name: str,
    identifier: str,
    admin_user: User = Depends(get_admin_user)
) -> RateLimitStatusResponse:
    """
    Get current rate limit status for a specific rule and identifier.
    
    Returns detailed information about token bucket status, utilization,
    and progressive limiting behavior if applicable.
    """
    status_data = enhanced_rate_limit_manager.get_rate_limit_status(rule_name, identifier)
    
    if "error" in status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=status_data["error"]
        )
    
    return RateLimitStatusResponse(**status_data)


@router.get("/analytics/{rule_name}/{identifier}", response_model=RateLimitAnalyticsResponse)
async def get_rate_limit_analytics(
    rule_name: str,
    identifier: str,
    window_minutes: int = Query(60, ge=1, le=1440, description="Analytics window in minutes"),
    admin_user: User = Depends(get_admin_user)
) -> RateLimitAnalyticsResponse:
    """
    Get analytics data for a specific rate limit rule and identifier.
    
    Returns request statistics, success rates, and usage patterns
    within the specified time window.
    """
    analytics_data = enhanced_rate_limit_manager.get_analytics(rule_name, identifier, window_minutes)
    
    if "error" in analytics_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=analytics_data["error"]
        )
    
    return RateLimitAnalyticsResponse(**analytics_data)


@router.post("/reset/{rule_name}/{identifier}")
async def reset_rate_limit_bucket(
    rule_name: str,
    identifier: str,
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, str]:
    """
    Reset a specific token bucket to full capacity.
    
    Admin-only endpoint for manually resetting rate limit buckets
    in case of issues or for testing purposes.
    """
    success = enhanced_rate_limit_manager.reset_bucket(rule_name, identifier)
    
    if success:
        return {
            "message": f"Rate limit bucket reset successfully",
            "rule_name": rule_name,
            "identifier": identifier
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit bucket not found for rule '{rule_name}' and identifier '{identifier}'"
        )


@router.get("/system/stats")
async def get_system_statistics(
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Get overall system statistics for rate limiting.
    
    Returns aggregate statistics about the rate limiting system including
    total rules, buckets, requests processed, and success rates.
    """
    return enhanced_rate_limit_manager.get_system_stats()


@router.get("/user/status")
async def get_user_rate_limit_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get rate limit status for the current user.
    
    Returns rate limit information relevant to the authenticated user
    including remaining tokens and reset times.
    """
    user_id = str(current_user.id)
    
    # Get status for user-specific rules
    user_status = enhanced_rate_limit_manager.get_rate_limit_status("user_requests", user_id)
    
    if "error" in user_status:
        # Return default status if no data available
        return {
            "user_id": user_id,
            "status": "No rate limit data available",
            "unlimited": True
        }
    
    return {
        "user_id": user_id,
        "rule_name": user_status["rule_name"],
        "tokens_remaining": user_status["tokens_remaining"],
        "capacity": user_status["capacity"],
        "refill_rate": user_status["refill_rate"],
        "utilization_percent": user_status["utilization_percent"],
        "unlimited": False
    }


@router.get("/test/{rule_name}/{identifier}")
async def test_rate_limit(
    rule_name: str,
    identifier: str,
    tokens: int = Query(1, ge=1, le=100, description="Number of tokens to consume"),
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Test rate limiting for a specific rule and identifier.
    
    Admin-only endpoint for testing rate limit behavior without
    affecting real traffic. Useful for validation and debugging.
    """
    result = await enhanced_rate_limit_manager.check_rate_limit(rule_name, identifier, tokens)
    
    return {
        "rule_name": result.rule_name,
        "scope": result.scope.value,
        "allowed": result.allowed,
        "tokens_remaining": result.tokens_remaining,
        "reset_time": result.reset_time,
        "retry_after": result.retry_after,
        "current_rate": result.current_rate,
        "reason": result.reason,
        "test_tokens_consumed": tokens
    }