"""
API Key Lifecycle Management

Advanced lifecycle management for API keys including expiration handling,
automated rotation, security monitoring, and lifecycle policies.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from ..models.api_key import APIKey, APIKeyStatus
from ..models.user import User
from ..core.api_keys import APIKeyManager
from ..core.database import async_session


logger = logging.getLogger(__name__)


class ExpirationPolicy(str, Enum):
    """API key expiration policies."""
    NEVER = "never"
    DAYS_30 = "30_days"
    DAYS_60 = "60_days"
    DAYS_90 = "90_days"
    DAYS_180 = "180_days"
    DAYS_365 = "365_days"
    CUSTOM = "custom"


class RotationTrigger(str, Enum):
    """Triggers for API key rotation."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    SECURITY_INCIDENT = "security_incident"
    USAGE_ANOMALY = "usage_anomaly"
    EXPIRATION_APPROACHING = "expiration_approaching"
    COMPLIANCE_REQUIREMENT = "compliance_requirement"


class LifecycleStatus(str, Enum):
    """Lifecycle status of API keys."""
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    ROTATION_NEEDED = "rotation_needed"
    ROTATION_IN_PROGRESS = "rotation_in_progress"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


@dataclass
class ExpirationNotification:
    """Container for expiration notification data."""
    api_key_id: str
    key_name: str
    user_id: str
    expires_at: datetime
    days_until_expiry: int
    notification_type: str  # warning, urgent, expired
    suggested_actions: List[str]


@dataclass
class RotationResult:
    """Result of an API key rotation operation."""
    success: bool
    old_key_id: str
    new_key_id: Optional[str]
    new_secret_key: Optional[str]
    rotation_trigger: RotationTrigger
    rotation_timestamp: datetime
    transition_period_days: int
    message: str
    errors: List[str] = None


class APIKeyLifecycleManager:
    """Manager for API key lifecycle operations."""
    
    def __init__(self):
        self.notification_thresholds = {
            "warning": 30,    # 30 days before expiry
            "urgent": 7,      # 7 days before expiry
            "critical": 1     # 1 day before expiry
        }
        
        self.rotation_policies = {
            "security_incident": {"immediate": True, "transition_days": 7},
            "compliance_requirement": {"immediate": False, "transition_days": 30},
            "scheduled": {"immediate": False, "transition_days": 14},
            "expiration_approaching": {"immediate": False, "transition_days": 30}
        }
    
    async def check_expiring_keys(
        self, 
        notification_days: int = 30
    ) -> List[ExpirationNotification]:
        """
        Check for API keys that are expiring soon.
        
        Args:
            notification_days: Number of days ahead to check for expiring keys
            
        Returns:
            List of expiration notifications
        """
        notifications = []
        
        try:
            async with async_session() as db:
                # Calculate the cutoff date
                cutoff_date = datetime.utcnow() + timedelta(days=notification_days)
                
                # Find keys expiring within the notification period
                query = select(APIKey).where(
                    and_(
                        APIKey.status == APIKeyStatus.active,
                        APIKey.expires_at.isnot(None),
                        APIKey.expires_at <= cutoff_date
                    )
                )
                
                result = await db.execute(query)
                expiring_keys = result.scalars().all()
                
                for api_key in expiring_keys:
                    days_until_expiry = (api_key.expires_at - datetime.utcnow()).days
                    
                    # Determine notification type
                    if days_until_expiry <= 0:
                        notification_type = "expired"
                    elif days_until_expiry <= self.notification_thresholds["critical"]:
                        notification_type = "critical"
                    elif days_until_expiry <= self.notification_thresholds["urgent"]:
                        notification_type = "urgent"
                    else:
                        notification_type = "warning"
                    
                    # Generate suggested actions
                    suggested_actions = self._get_expiration_actions(notification_type, days_until_expiry)
                    
                    notification = ExpirationNotification(
                        api_key_id=str(api_key.id),
                        key_name=api_key.name,
                        user_id=str(api_key.user_id),
                        expires_at=api_key.expires_at,
                        days_until_expiry=days_until_expiry,
                        notification_type=notification_type,
                        suggested_actions=suggested_actions
                    )
                    
                    notifications.append(notification)
                
                logger.info(f"Found {len(notifications)} expiring API keys")
                
        except Exception as e:
            logger.error(f"Failed to check expiring keys: {e}")
        
        return notifications
    
    async def expire_old_keys(self) -> List[str]:
        """
        Automatically expire API keys that have passed their expiration date.
        
        Returns:
            List of expired API key IDs
        """
        expired_key_ids = []
        
        try:
            async with async_session() as db:
                now = datetime.utcnow()
                
                # Find keys that have expired
                query = select(APIKey).where(
                    and_(
                        APIKey.status == APIKeyStatus.active,
                        APIKey.expires_at.isnot(None),
                        APIKey.expires_at <= now
                    )
                )
                
                result = await db.execute(query)
                expired_keys = result.scalars().all()
                
                for api_key in expired_keys:
                    # Update key status to expired
                    await db.execute(
                        update(APIKey)
                        .where(APIKey.id == api_key.id)
                        .values(
                            status=APIKeyStatus.expired,
                            updated_at=now
                        )
                    )
                    
                    expired_key_ids.append(str(api_key.id))
                    
                    logger.info(f"Expired API key: {api_key.key_id} ({api_key.name})")
                
                await db.commit()
                
                logger.info(f"Expired {len(expired_key_ids)} API keys")
                
        except Exception as e:
            logger.error(f"Failed to expire old keys: {e}")
        
        return expired_key_ids
    
    async def rotate_api_key(
        self,
        api_key_id: str,
        trigger: RotationTrigger,
        user_id: Optional[str] = None,
        new_name: Optional[str] = None,
        transition_days: Optional[int] = None,
        preserve_settings: bool = True
    ) -> RotationResult:
        """
        Rotate an API key with advanced lifecycle management.
        
        Args:
            api_key_id: ID of the API key to rotate
            trigger: What triggered the rotation
            user_id: User ID for ownership verification
            new_name: Optional new name for the rotated key
            transition_days: Days to keep old key active during transition
            preserve_settings: Whether to preserve rate limits and permissions
            
        Returns:
            RotationResult with operation details
        """
        try:
            async with async_session() as db:
                # Get the existing API key
                query = select(APIKey).where(APIKey.id == api_key_id)
                if user_id:
                    query = query.where(APIKey.user_id == user_id)
                
                result = await db.execute(query)
                old_api_key = result.scalar_one_or_none()
                
                if not old_api_key:
                    return RotationResult(
                        success=False,
                        old_key_id=api_key_id,
                        new_key_id=None,
                        new_secret_key=None,
                        rotation_trigger=trigger,
                        rotation_timestamp=datetime.utcnow(),
                        transition_period_days=0,
                        message="API key not found",
                        errors=["API key not found or access denied"]
                    )
                
                # Get rotation policy for this trigger
                policy = self.rotation_policies.get(trigger.value, {
                    "immediate": False,
                    "transition_days": 14
                })
                
                # Determine transition period
                if transition_days is None:
                    transition_days = policy.get("transition_days", 14)
                
                # Generate new key pair
                key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
                
                # Determine new key name
                if not new_name:
                    timestamp = datetime.utcnow().strftime("%Y%m%d")
                    new_name = f"{old_api_key.name} (Rotated {timestamp})"
                
                # Create new API key
                new_api_key_data = {
                    "key_id": key_id,
                    "key_hash": key_hash,
                    "name": new_name,
                    "user_id": old_api_key.user_id,
                    "status": APIKeyStatus.active
                }
                
                # Preserve settings if requested
                if preserve_settings:
                    new_api_key_data.update({
                        "description": f"Rotated from {old_api_key.name}",
                        "scopes": old_api_key.scopes,
                        "allowed_ips": old_api_key.allowed_ips,
                        "allowed_domains": old_api_key.allowed_domains,
                        "rate_limit": old_api_key.rate_limit,
                        "rate_limit_period": old_api_key.rate_limit_period,
                        "extra_data": old_api_key.extra_data or {}
                    })
                    
                    # Set expiration if old key had one
                    if old_api_key.expires_at:
                        # Extend expiration from current date
                        days_remaining = (old_api_key.expires_at - datetime.utcnow()).days
                        if days_remaining > 0:
                            new_api_key_data["expires_at"] = datetime.utcnow() + timedelta(days=max(days_remaining, 30))
                
                new_api_key = APIKey(**new_api_key_data)
                db.add(new_api_key)
                
                # Handle old key based on policy
                if policy.get("immediate", False):
                    # Immediately revoke old key for security incidents
                    old_api_key.status = APIKeyStatus.revoked
                    old_api_key.updated_at = datetime.utcnow()
                    transition_message = "Old key immediately revoked due to security concern"
                else:
                    # Mark old key as deprecated with transition period
                    old_api_key.status = APIKeyStatus.suspended  # Use suspended as deprecated
                    old_api_key.updated_at = datetime.utcnow()
                    
                    # Set expiration for transition period
                    transition_end = datetime.utcnow() + timedelta(days=transition_days)
                    old_api_key.expires_at = transition_end
                    
                    transition_message = f"Old key will be revoked after {transition_days} day transition period"
                
                # Add rotation metadata to both keys
                rotation_metadata = {
                    "rotation_trigger": trigger.value,
                    "rotation_timestamp": datetime.utcnow().isoformat(),
                    "transition_days": transition_days
                }
                
                if old_api_key.extra_data:
                    old_api_key.extra_data.update({"deprecated_by": key_id, **rotation_metadata})
                else:
                    old_api_key.extra_data = {"deprecated_by": key_id, **rotation_metadata}
                
                if new_api_key.extra_data:
                    new_api_key.extra_data.update({"replaces": old_api_key.key_id, **rotation_metadata})
                else:
                    new_api_key.extra_data = {"replaces": old_api_key.key_id, **rotation_metadata}
                
                await db.commit()
                await db.refresh(new_api_key)
                
                logger.info(f"Rotated API key {old_api_key.key_id} -> {new_api_key.key_id} (trigger: {trigger.value})")
                
                return RotationResult(
                    success=True,
                    old_key_id=old_api_key.key_id,
                    new_key_id=new_api_key.key_id,
                    new_secret_key=secret_key,
                    rotation_trigger=trigger,
                    rotation_timestamp=datetime.utcnow(),
                    transition_period_days=transition_days,
                    message=f"API key rotated successfully. {transition_message}",
                    errors=[]
                )
                
        except Exception as e:
            logger.error(f"Failed to rotate API key: {e}")
            return RotationResult(
                success=False,
                old_key_id=api_key_id,
                new_key_id=None,
                new_secret_key=None,
                rotation_trigger=trigger,
                rotation_timestamp=datetime.utcnow(),
                transition_period_days=0,
                message=f"Rotation failed: {str(e)}",
                errors=[str(e)]
            )
    
    async def schedule_auto_rotation(
        self,
        api_key_id: str,
        rotation_interval_days: int,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Schedule automatic rotation for an API key.
        
        Args:
            api_key_id: ID of the API key
            rotation_interval_days: Days between automatic rotations
            user_id: User ID for ownership verification
            
        Returns:
            True if scheduled successfully
        """
        try:
            async with async_session() as db:
                # Get the API key
                query = select(APIKey).where(APIKey.id == api_key_id)
                if user_id:
                    query = query.where(APIKey.user_id == user_id)
                
                result = await db.execute(query)
                api_key = result.scalar_one_or_none()
                
                if not api_key:
                    return False
                
                # Add rotation schedule to metadata
                next_rotation = datetime.utcnow() + timedelta(days=rotation_interval_days)
                
                rotation_schedule = {
                    "auto_rotation_enabled": True,
                    "rotation_interval_days": rotation_interval_days,
                    "next_rotation_date": next_rotation.isoformat(),
                    "scheduled_at": datetime.utcnow().isoformat()
                }
                
                if api_key.extra_data:
                    api_key.extra_data.update(rotation_schedule)
                else:
                    api_key.extra_data = rotation_schedule
                
                api_key.updated_at = datetime.utcnow()
                
                await db.commit()
                
                logger.info(f"Scheduled auto-rotation for API key {api_key.key_id} every {rotation_interval_days} days")
                return True
                
        except Exception as e:
            logger.error(f"Failed to schedule auto-rotation: {e}")
            return False
    
    async def process_scheduled_rotations(self) -> List[RotationResult]:
        """
        Process all scheduled automatic rotations.
        
        Returns:
            List of rotation results
        """
        rotation_results = []
        
        try:
            async with async_session() as db:
                now = datetime.utcnow()
                
                # Find keys with scheduled rotations
                query = select(APIKey).where(
                    and_(
                        APIKey.status == APIKeyStatus.active,
                        APIKey.extra_data.isnot(None)
                    )
                )
                
                result = await db.execute(query)
                api_keys = result.scalars().all()
                
                for api_key in api_keys:
                    if not api_key.extra_data:
                        continue
                    
                    # Check if auto-rotation is enabled and due
                    auto_rotation = api_key.extra_data.get("auto_rotation_enabled", False)
                    next_rotation_str = api_key.extra_data.get("next_rotation_date")
                    
                    if auto_rotation and next_rotation_str:
                        try:
                            next_rotation = datetime.fromisoformat(next_rotation_str.replace('Z', '+00:00'))
                            if now >= next_rotation:
                                # Perform rotation
                                rotation_result = await self.rotate_api_key(
                                    str(api_key.id),
                                    RotationTrigger.SCHEDULED,
                                    preserve_settings=True
                                )
                                
                                rotation_results.append(rotation_result)
                                
                                if rotation_result.success:
                                    # Schedule next rotation
                                    interval_days = api_key.extra_data.get("rotation_interval_days", 90)
                                    await self.schedule_auto_rotation(
                                        str(api_key.id),
                                        interval_days
                                    )
                        except (ValueError, TypeError) as e:
                            logger.error(f"Invalid rotation date format for key {api_key.key_id}: {e}")
                
                logger.info(f"Processed {len(rotation_results)} scheduled rotations")
                
        except Exception as e:
            logger.error(f"Failed to process scheduled rotations: {e}")
        
        return rotation_results
    
    async def get_lifecycle_status(self, api_key_id: str) -> Dict[str, Any]:
        """
        Get comprehensive lifecycle status for an API key.
        
        Args:
            api_key_id: ID of the API key
            
        Returns:
            Dictionary with lifecycle information
        """
        try:
            async with async_session() as db:
                query = select(APIKey).where(APIKey.id == api_key_id)
                result = await db.execute(query)
                api_key = result.scalar_one_or_none()
                
                if not api_key:
                    return {"error": "API key not found"}
                
                now = datetime.utcnow()
                
                # Determine lifecycle status
                if api_key.status == APIKeyStatus.revoked:
                    lifecycle_status = LifecycleStatus.REVOKED
                elif api_key.status == APIKeyStatus.expired:
                    lifecycle_status = LifecycleStatus.EXPIRED
                elif api_key.status == APIKeyStatus.suspended:
                    lifecycle_status = LifecycleStatus.DEPRECATED
                elif api_key.expires_at:
                    days_until_expiry = (api_key.expires_at - now).days
                    if days_until_expiry <= 0:
                        lifecycle_status = LifecycleStatus.EXPIRED
                    elif days_until_expiry <= 7:
                        lifecycle_status = LifecycleStatus.EXPIRING_SOON
                    else:
                        lifecycle_status = LifecycleStatus.ACTIVE
                else:
                    lifecycle_status = LifecycleStatus.ACTIVE
                
                # Check for rotation scheduling
                auto_rotation_enabled = False
                next_rotation_date = None
                if api_key.extra_data:
                    auto_rotation_enabled = api_key.extra_data.get("auto_rotation_enabled", False)
                    next_rotation_str = api_key.extra_data.get("next_rotation_date")
                    if next_rotation_str:
                        try:
                            next_rotation_date = datetime.fromisoformat(next_rotation_str.replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            pass
                
                return {
                    "api_key_id": api_key.key_id,
                    "lifecycle_status": lifecycle_status.value,
                    "current_status": api_key.status.value,
                    "created_at": api_key.created_at.isoformat(),
                    "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                    "days_until_expiry": (api_key.expires_at - now).days if api_key.expires_at else None,
                    "auto_rotation": {
                        "enabled": auto_rotation_enabled,
                        "next_rotation": next_rotation_date.isoformat() if next_rotation_date else None,
                        "days_until_rotation": (next_rotation_date - now).days if next_rotation_date else None
                    },
                    "rotation_history": api_key.extra_data.get("rotation_history", []) if api_key.extra_data else [],
                    "recommendations": self._get_lifecycle_recommendations(api_key, lifecycle_status)
                }
                
        except Exception as e:
            logger.error(f"Failed to get lifecycle status: {e}")
            return {"error": str(e)}
    
    def _get_expiration_actions(self, notification_type: str, days_until_expiry: int) -> List[str]:
        """Get suggested actions for expiration notifications."""
        if notification_type == "expired":
            return [
                "API key has expired and is no longer valid",
                "Create a new API key immediately",
                "Update your applications with the new key",
                "Contact support if you need help"
            ]
        elif notification_type == "critical":
            return [
                f"API key expires in {days_until_expiry} day(s)",
                "Rotate the key immediately",
                "Update your applications with the new key",
                "Test the new key before the old one expires"
            ]
        elif notification_type == "urgent":
            return [
                f"API key expires in {days_until_expiry} days",
                "Plan key rotation within the next few days",
                "Prepare to update your applications",
                "Consider enabling auto-rotation for the future"
            ]
        else:  # warning
            return [
                f"API key expires in {days_until_expiry} days",
                "Schedule key rotation in the coming weeks",
                "Review key usage and permissions",
                "Consider setting up auto-rotation"
            ]
    
    def _get_lifecycle_recommendations(self, api_key: APIKey, status: LifecycleStatus) -> List[str]:
        """Get lifecycle recommendations for an API key."""
        recommendations = []
        
        if status == LifecycleStatus.EXPIRING_SOON:
            recommendations.append("Consider rotating the key soon to avoid service interruption")
            recommendations.append("Enable auto-rotation for future keys")
        elif status == LifecycleStatus.ACTIVE:
            if not api_key.expires_at:
                recommendations.append("Consider setting an expiration date for security")
            
            auto_rotation = api_key.extra_data.get("auto_rotation_enabled", False) if api_key.extra_data else False
            if not auto_rotation:
                recommendations.append("Enable auto-rotation for better security")
        elif status == LifecycleStatus.EXPIRED:
            recommendations.append("Create a new API key to restore service")
            recommendations.append("Update your applications with the new key")
        
        # General security recommendations
        if api_key.scopes and "admin" in api_key.scopes:
            recommendations.append("Review admin permissions regularly")
        
        if not api_key.allowed_ips:
            recommendations.append("Consider restricting access to specific IP addresses")
        
        return recommendations


# Background service for lifecycle management
class LifecycleService:
    """Background service for API key lifecycle management."""
    
    def __init__(self, check_interval_minutes: int = 60):
        self.check_interval_minutes = check_interval_minutes
        self.manager = APIKeyLifecycleManager()
        self.running = False
    
    async def start(self):
        """Start the lifecycle management service."""
        self.running = True
        asyncio.create_task(self._lifecycle_check_loop())
        logger.info("API key lifecycle service started")
    
    async def stop(self):
        """Stop the lifecycle management service."""
        self.running = False
        logger.info("API key lifecycle service stopped")
    
    async def _lifecycle_check_loop(self):
        """Main loop for lifecycle checks."""
        while self.running:
            try:
                # Check for expiring keys
                await self.manager.check_expiring_keys()
                
                # Expire old keys
                await self.manager.expire_old_keys()
                
                # Process scheduled rotations
                await self.manager.process_scheduled_rotations()
                
                # Wait for next check
                await asyncio.sleep(self.check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in lifecycle check loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying


# Global lifecycle service instance
_lifecycle_service: Optional[LifecycleService] = None


def get_lifecycle_service() -> LifecycleService:
    """Get the global lifecycle service instance."""
    global _lifecycle_service
    if _lifecycle_service is None:
        _lifecycle_service = LifecycleService()
    return _lifecycle_service


async def start_lifecycle_service():
    """Start the lifecycle management service."""
    service = get_lifecycle_service()
    await service.start()


async def stop_lifecycle_service():
    """Stop the lifecycle management service."""
    service = get_lifecycle_service()
    await service.stop()