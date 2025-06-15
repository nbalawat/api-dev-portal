"""
API Key Lifecycle Management Router

API endpoints for managing API key lifecycles including expiration,
rotation, scheduling, and lifecycle monitoring.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.key_lifecycle import (
    APIKeyLifecycleManager, ExpirationPolicy, RotationTrigger,
    LifecycleStatus, ExpirationNotification, RotationResult
)
from ..middleware.permissions import require_resource_permission, get_permission_checker, PermissionChecker
from ..middleware import require_api_key
from ..core.permissions import ResourceType, Permission
from ..models.api_key import APIKey
from ..dependencies.database import get_database


router = APIRouter(prefix="/lifecycle")


# Request/Response Models
class RotationRequest(BaseModel):
    """Request model for manual API key rotation."""
    trigger: RotationTrigger = RotationTrigger.MANUAL
    new_name: Optional[str] = None
    transition_days: Optional[int] = None
    preserve_settings: bool = True


class AutoRotationRequest(BaseModel):
    """Request model for setting up auto-rotation."""
    enabled: bool
    rotation_interval_days: int = 90
    transition_days: int = 14


class ExpirationRequest(BaseModel):
    """Request model for setting API key expiration."""
    expires_at: Optional[datetime] = None
    expiration_policy: ExpirationPolicy = ExpirationPolicy.NEVER


class LifecycleStatusResponse(BaseModel):
    """Response model for lifecycle status."""
    api_key_id: str
    lifecycle_status: str
    current_status: str
    created_at: str
    expires_at: Optional[str]
    days_until_expiry: Optional[int]
    auto_rotation: Dict[str, Any]
    rotation_history: List[Dict[str, Any]]
    recommendations: List[str]


class RotationResponse(BaseModel):
    """Response model for rotation operations."""
    success: bool
    old_key_id: str
    new_key_id: Optional[str]
    new_secret_key: Optional[str]
    rotation_trigger: str
    rotation_timestamp: str
    transition_period_days: int
    message: str
    errors: Optional[List[str]]


class ExpirationCheckResponse(BaseModel):
    """Response model for expiration checks."""
    total_expiring_keys: int
    notifications: List[Dict[str, Any]]
    summary: Dict[str, int]


# Public endpoints (require API key management permissions)
@router.get("/status/{api_key_id}", response_model=LifecycleStatusResponse)
async def get_lifecycle_status(
    api_key_id: str,
    current_api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get lifecycle status for a specific API key.
    
    Returns comprehensive information about the key's lifecycle including
    expiration, rotation schedule, and recommendations.
    """
    # Check if user can access this API key
    checker = PermissionChecker(current_api_key)
    
    # Admin can check any key, users can only check their own
    if not checker.can(ResourceType.API_KEY, Permission.MANAGE):
        # Verify ownership by checking if the requested key belongs to the same user
        from sqlalchemy import select
        query = select(APIKey).where(APIKey.id == api_key_id)
        result = await db.execute(query)
        target_key = result.scalar_one_or_none()
        
        if not target_key or target_key.user_id != current_api_key.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this API key"
            )
    
    manager = APIKeyLifecycleManager()
    lifecycle_status = await manager.get_lifecycle_status(api_key_id)
    
    if "error" in lifecycle_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=lifecycle_status["error"]
        )
    
    return LifecycleStatusResponse(**lifecycle_status)


@router.get("/my-keys/status")
async def get_my_keys_lifecycle_status(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get lifecycle status for all API keys belonging to the current user.
    
    Returns summary of all keys with their lifecycle information.
    """
    from sqlalchemy import select
    
    # Get all API keys for the current user
    query = select(APIKey).where(APIKey.user_id == api_key.user_id)
    result = await db.execute(query)
    user_keys = result.scalars().all()
    
    manager = APIKeyLifecycleManager()
    key_statuses = []
    
    for user_key in user_keys:
        lifecycle_status = await manager.get_lifecycle_status(str(user_key.id))
        if "error" not in lifecycle_status:
            key_statuses.append(lifecycle_status)
    
    # Generate summary statistics
    total_keys = len(key_statuses)
    active_keys = len([k for k in key_statuses if k["lifecycle_status"] == "active"])
    expiring_soon = len([k for k in key_statuses if k["lifecycle_status"] == "expiring_soon"])
    expired_keys = len([k for k in key_statuses if k["lifecycle_status"] == "expired"])
    auto_rotation_enabled = len([k for k in key_statuses if k["auto_rotation"]["enabled"]])
    
    return {
        "user_id": str(api_key.user_id),
        "summary": {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expiring_soon": expiring_soon,
            "expired_keys": expired_keys,
            "auto_rotation_enabled": auto_rotation_enabled
        },
        "keys": key_statuses
    }


@router.post("/rotate/{api_key_id}", response_model=RotationResponse)
async def rotate_api_key(
    api_key_id: str,
    rotation_request: RotationRequest,
    current_api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.UPDATE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Manually rotate an API key.
    
    Creates a new API key with the same settings and manages the transition
    from the old key to the new key.
    """
    # Check ownership unless admin
    checker = PermissionChecker(current_api_key)
    user_id = None if checker.can(ResourceType.API_KEY, Permission.MANAGE) else str(current_api_key.user_id)
    
    manager = APIKeyLifecycleManager()
    
    rotation_result = await manager.rotate_api_key(
        api_key_id=api_key_id,
        trigger=rotation_request.trigger,
        user_id=user_id,
        new_name=rotation_request.new_name,
        transition_days=rotation_request.transition_days,
        preserve_settings=rotation_request.preserve_settings
    )
    
    return RotationResponse(
        success=rotation_result.success,
        old_key_id=rotation_result.old_key_id,
        new_key_id=rotation_result.new_key_id,
        new_secret_key=rotation_result.new_secret_key,
        rotation_trigger=rotation_result.rotation_trigger.value,
        rotation_timestamp=rotation_result.rotation_timestamp.isoformat(),
        transition_period_days=rotation_result.transition_period_days,
        message=rotation_result.message,
        errors=rotation_result.errors
    )


@router.post("/auto-rotation/{api_key_id}")
async def setup_auto_rotation(
    api_key_id: str,
    auto_rotation_request: AutoRotationRequest,
    current_api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.UPDATE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Setup or modify auto-rotation for an API key.
    
    Configures automatic rotation schedule with specified intervals.
    """
    # Check ownership unless admin
    checker = PermissionChecker(current_api_key)
    user_id = None if checker.can(ResourceType.API_KEY, Permission.MANAGE) else str(current_api_key.user_id)
    
    manager = APIKeyLifecycleManager()
    
    if auto_rotation_request.enabled:
        success = await manager.schedule_auto_rotation(
            api_key_id=api_key_id,
            rotation_interval_days=auto_rotation_request.rotation_interval_days,
            user_id=user_id
        )
        
        if success:
            return {
                "message": "Auto-rotation scheduled successfully",
                "api_key_id": api_key_id,
                "rotation_interval_days": auto_rotation_request.rotation_interval_days,
                "next_rotation": (datetime.utcnow() + timedelta(days=auto_rotation_request.rotation_interval_days)).isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to schedule auto-rotation"
            )
    else:
        # Disable auto-rotation
        from sqlalchemy import select, update
        from ..models.api_key import APIKey as APIKeyModel
        
        query = select(APIKeyModel).where(APIKeyModel.id == api_key_id)
        if user_id:
            query = query.where(APIKeyModel.user_id == user_id)
        
        result = await db.execute(query)
        api_key_obj = result.scalar_one_or_none()
        
        if not api_key_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Remove auto-rotation from metadata
        if api_key_obj.extra_data:
            api_key_obj.extra_data.pop("auto_rotation_enabled", None)
            api_key_obj.extra_data.pop("rotation_interval_days", None)
            api_key_obj.extra_data.pop("next_rotation_date", None)
        
        api_key_obj.updated_at = datetime.utcnow()
        await db.commit()
        
        return {
            "message": "Auto-rotation disabled",
            "api_key_id": api_key_id
        }


@router.put("/expiration/{api_key_id}")
async def set_expiration(
    api_key_id: str,
    expiration_request: ExpirationRequest,
    current_api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.UPDATE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Set or update expiration for an API key.
    
    Configures when the API key should expire based on policy or specific date.
    """
    # Check ownership unless admin
    checker = PermissionChecker(current_api_key)
    user_id = None if checker.can(ResourceType.API_KEY, Permission.MANAGE) else str(current_api_key.user_id)
    
    from sqlalchemy import select, update
    from ..models.api_key import APIKey as APIKeyModel
    
    query = select(APIKeyModel).where(APIKeyModel.id == api_key_id)
    if user_id:
        query = query.where(APIKeyModel.user_id == user_id)
    
    result = await db.execute(query)
    api_key_obj = result.scalar_one_or_none()
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Calculate expiration date based on policy
    if expiration_request.expiration_policy == ExpirationPolicy.NEVER:
        new_expiration = None
    elif expiration_request.expires_at:
        new_expiration = expiration_request.expires_at
    else:
        # Use policy to calculate expiration
        days_mapping = {
            ExpirationPolicy.DAYS_30: 30,
            ExpirationPolicy.DAYS_60: 60,
            ExpirationPolicy.DAYS_90: 90,
            ExpirationPolicy.DAYS_180: 180,
            ExpirationPolicy.DAYS_365: 365
        }
        
        days = days_mapping.get(expiration_request.expiration_policy, 90)
        new_expiration = datetime.utcnow() + timedelta(days=days)
    
    # Update expiration
    api_key_obj.expires_at = new_expiration
    api_key_obj.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": "Expiration updated successfully",
        "api_key_id": api_key_id,
        "expires_at": new_expiration.isoformat() if new_expiration else None,
        "policy": expiration_request.expiration_policy.value
    }


# Admin endpoints
@router.get("/admin/expiring-keys", response_model=ExpirationCheckResponse)
async def check_expiring_keys(
    notification_days: int = Query(30, ge=1, le=365),
    admin_api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Check for API keys expiring within specified timeframe (admin only).
    
    Returns comprehensive report of expiring keys across all users.
    """
    manager = APIKeyLifecycleManager()
    notifications = await manager.check_expiring_keys(notification_days)
    
    # Generate summary
    total_expiring = len(notifications)
    by_type = {"warning": 0, "urgent": 0, "critical": 0, "expired": 0}
    
    notification_data = []
    for notification in notifications:
        by_type[notification.notification_type] += 1
        notification_data.append({
            "api_key_id": notification.api_key_id,
            "key_name": notification.key_name,
            "user_id": notification.user_id,
            "expires_at": notification.expires_at.isoformat(),
            "days_until_expiry": notification.days_until_expiry,
            "notification_type": notification.notification_type,
            "suggested_actions": notification.suggested_actions
        })
    
    return ExpirationCheckResponse(
        total_expiring_keys=total_expiring,
        notifications=notification_data,
        summary=by_type
    )


@router.post("/admin/expire-old-keys")
async def expire_old_keys(
    admin_api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.MANAGE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Manually trigger expiration of all overdue API keys (admin only).
    
    Forces expiration of keys that have passed their expiration date.
    """
    manager = APIKeyLifecycleManager()
    expired_key_ids = await manager.expire_old_keys()
    
    return {
        "message": "Old keys expired",
        "expired_count": len(expired_key_ids),
        "expired_key_ids": expired_key_ids,
        "processed_at": datetime.utcnow().isoformat()
    }


@router.post("/admin/process-rotations")
async def process_scheduled_rotations(
    admin_api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.MANAGE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Manually trigger processing of scheduled rotations (admin only).
    
    Processes all due automatic rotations immediately.
    """
    manager = APIKeyLifecycleManager()
    rotation_results = await manager.process_scheduled_rotations()
    
    successful_rotations = [r for r in rotation_results if r.success]
    failed_rotations = [r for r in rotation_results if not r.success]
    
    return {
        "message": "Scheduled rotations processed",
        "total_processed": len(rotation_results),
        "successful": len(successful_rotations),
        "failed": len(failed_rotations),
        "results": [
            {
                "success": r.success,
                "old_key_id": r.old_key_id,
                "new_key_id": r.new_key_id,
                "message": r.message,
                "errors": r.errors
            }
            for r in rotation_results
        ],
        "processed_at": datetime.utcnow().isoformat()
    }


@router.get("/admin/lifecycle-stats")
async def get_lifecycle_statistics(
    admin_api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.READ)),
    db: AsyncSession = Depends(get_database)
):
    """
    Get system-wide lifecycle statistics (admin only).
    
    Returns comprehensive statistics about API key lifecycles across the system.
    """
    from sqlalchemy import select, func
    from ..models.api_key import APIKey as APIKeyModel, APIKeyStatus
    
    # Get basic statistics
    total_keys_query = select(func.count(APIKeyModel.id))
    total_keys_result = await db.execute(total_keys_query)
    total_keys = total_keys_result.scalar()
    
    # Keys by status
    status_query = select(
        APIKeyModel.status,
        func.count(APIKeyModel.id)
    ).group_by(APIKeyModel.status)
    status_result = await db.execute(status_query)
    status_counts = {row[0].value: row[1] for row in status_result.fetchall()}
    
    # Keys with expiration
    now = datetime.utcnow()
    expiring_soon_query = select(func.count(APIKeyModel.id)).where(
        APIKeyModel.expires_at.between(now, now + timedelta(days=30))
    )
    expiring_soon_result = await db.execute(expiring_soon_query)
    expiring_soon = expiring_soon_result.scalar()
    
    # Keys with auto-rotation enabled
    # This would require JSON queries which depend on the database backend
    # For now, we'll return a placeholder
    
    return {
        "total_api_keys": total_keys,
        "status_distribution": status_counts,
        "expiring_within_30_days": expiring_soon,
        "auto_rotation_enabled": 0,  # Placeholder
        "recent_rotations": 0,       # Placeholder
        "generated_at": datetime.utcnow().isoformat()
    }


# Utility endpoints
@router.get("/policies")
async def get_lifecycle_policies(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get available lifecycle policies and configurations.
    
    Returns information about expiration policies, rotation triggers, and best practices.
    """
    return {
        "expiration_policies": [
            {
                "name": policy.value,
                "description": {
                    "never": "Key never expires (not recommended for production)",
                    "30_days": "Key expires after 30 days",
                    "60_days": "Key expires after 60 days", 
                    "90_days": "Key expires after 90 days (recommended)",
                    "180_days": "Key expires after 180 days",
                    "365_days": "Key expires after 1 year",
                    "custom": "Custom expiration date"
                }.get(policy.value, "")
            }
            for policy in ExpirationPolicy
        ],
        "rotation_triggers": [
            {
                "name": trigger.value,
                "description": {
                    "manual": "Manual rotation initiated by user",
                    "scheduled": "Automatic rotation on schedule",
                    "security_incident": "Emergency rotation due to security incident",
                    "usage_anomaly": "Rotation due to unusual usage patterns",
                    "expiration_approaching": "Proactive rotation before expiration",
                    "compliance_requirement": "Rotation for compliance purposes"
                }.get(trigger.value, "")
            }
            for trigger in RotationTrigger
        ],
        "best_practices": [
            "Set expiration dates for all production keys",
            "Enable auto-rotation with 90-day intervals",
            "Use transition periods for zero-downtime rotation",
            "Monitor key usage for anomalies",
            "Restrict key access to specific IP addresses",
            "Regularly audit key permissions and scopes",
            "Implement proper key storage and handling"
        ],
        "recommended_settings": {
            "expiration_policy": "90_days",
            "auto_rotation_interval": 90,
            "transition_period": 14,
            "notification_thresholds": {
                "warning": 30,
                "urgent": 7,
                "critical": 1
            }
        }
    }