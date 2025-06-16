"""
API Key Expiration Management Service

This service handles automated checking and notification of expiring API keys,
including scheduled warnings, automatic expiration, and policy enforcement.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from pydantic import BaseModel
from enum import Enum

from ..models.api_key import APIKey, APIKeyStatus
from ..models.user import User
from ..dependencies.database import get_database
from ..services.email import email_service
from ..core.config import settings


class ExpirationNotificationLevel(str, Enum):
    """Levels of expiration notifications."""
    WARNING_30_DAYS = "warning_30_days"    # 30 days before expiration
    WARNING_7_DAYS = "warning_7_days"      # 7 days before expiration
    CRITICAL_1_DAY = "critical_1_day"      # 1 day before expiration
    EXPIRED = "expired"                    # Already expired


class ExpirationWarning(BaseModel):
    """Model for expiration warning data."""
    api_key_id: str
    key_name: str
    key_id: str
    user_email: str
    username: str
    expires_at: datetime
    days_until_expiry: int
    notification_level: ExpirationNotificationLevel
    last_warning_sent: Optional[datetime] = None


class ExpirationPolicy(BaseModel):
    """Policy configuration for key expiration."""
    default_expiration_days: int = 90
    warning_days: List[int] = [30, 7, 1]  # Days before expiration to send warnings
    auto_disable_expired: bool = True
    grace_period_hours: int = 24  # Hours after expiration before auto-disable
    max_expiration_days: int = 365  # Maximum allowed expiration period


class ExpirationManager:
    """Service for managing API key expiration warnings and automation."""
    
    def __init__(self):
        self.policy = ExpirationPolicy()
        self.notification_tracking = {}  # Track when notifications were sent
    
    async def check_expiring_keys(self, db: AsyncSession) -> List[ExpirationWarning]:
        """
        Check for API keys that are expiring soon or already expired.
        
        Args:
            db: Database session
            
        Returns:
            List of expiration warnings
        """
        now = datetime.utcnow()
        
        # Calculate warning thresholds
        warning_dates = []
        for days in self.policy.warning_days:
            warning_dates.append(now + timedelta(days=days))
        
        # Add grace period for expired keys
        grace_period_end = now - timedelta(hours=self.policy.grace_period_hours)
        
        # Query for keys that need attention
        query = select(APIKey, User).join(User).where(
            and_(
                APIKey.status == APIKeyStatus.active,
                APIKey.expires_at.isnot(None),
                or_(
                    # Keys expiring within warning periods
                    and_(
                        APIKey.expires_at <= max(warning_dates),
                        APIKey.expires_at > now
                    ),
                    # Keys that are expired but within grace period
                    and_(
                        APIKey.expires_at <= now,
                        APIKey.expires_at > grace_period_end
                    )
                )
            )
        )
        
        result = await db.execute(query)
        key_user_pairs = result.fetchall()
        
        warnings = []
        for api_key, user in key_user_pairs:
            days_until_expiry = (api_key.expires_at - now).days
            
            # Determine notification level
            if days_until_expiry <= 0:
                level = ExpirationNotificationLevel.EXPIRED
            elif days_until_expiry <= 1:
                level = ExpirationNotificationLevel.CRITICAL_1_DAY
            elif days_until_expiry <= 7:
                level = ExpirationNotificationLevel.WARNING_7_DAYS
            else:
                level = ExpirationNotificationLevel.WARNING_30_DAYS
            
            warnings.append(ExpirationWarning(
                api_key_id=str(api_key.id),
                key_name=api_key.name,
                key_id=api_key.key_id,
                user_email=user.email,
                username=user.username,
                expires_at=api_key.expires_at,
                days_until_expiry=days_until_expiry,
                notification_level=level
            ))
        
        return warnings
    
    async def send_expiration_notifications(
        self, 
        warnings: List[ExpirationWarning],
        force_send: bool = False
    ) -> Dict[str, int]:
        """
        Send expiration notifications for the given warnings.
        
        Args:
            warnings: List of expiration warnings
            force_send: Send notifications even if recently sent
            
        Returns:
            Dictionary with counts of notifications sent by level
        """
        notification_counts = {
            "warning_30_days": 0,
            "warning_7_days": 0,
            "critical_1_day": 0,
            "expired": 0,
            "skipped": 0,
            "failed": 0
        }
        
        for warning in warnings:
            # Check if we recently sent a notification for this key
            key_tracking_id = f"{warning.api_key_id}_{warning.notification_level.value}"
            
            if not force_send and key_tracking_id in self.notification_tracking:
                last_sent = self.notification_tracking[key_tracking_id]
                # Don't send same level notification more than once per day
                if (datetime.utcnow() - last_sent).total_seconds() < 86400:  # 24 hours
                    notification_counts["skipped"] += 1
                    continue
            
            try:
                # Send appropriate notification
                if warning.notification_level == ExpirationNotificationLevel.EXPIRED:
                    success = await self._send_expired_notification(warning)
                else:
                    success = await self._send_expiring_notification(warning)
                
                if success:
                    notification_counts[warning.notification_level.value] += 1
                    # Track that we sent this notification
                    self.notification_tracking[key_tracking_id] = datetime.utcnow()
                else:
                    notification_counts["failed"] += 1
                    
            except Exception as e:
                print(f"Failed to send expiration notification for key {warning.key_id}: {e}")
                notification_counts["failed"] += 1
        
        return notification_counts
    
    async def _send_expiring_notification(self, warning: ExpirationWarning) -> bool:
        """Send expiring notification via email."""
        try:
            expires_at_str = warning.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            return email_service.send_api_key_expiring_notification(
                email=warning.user_email,
                username=warning.username,
                key_name=warning.key_name,
                key_id=warning.key_id,
                expires_at=expires_at_str,
                days_until_expiry=warning.days_until_expiry
            )
        except Exception as e:
            print(f"Error sending expiring notification: {e}")
            return False
    
    async def _send_expired_notification(self, warning: ExpirationWarning) -> bool:
        """Send expired notification via email."""
        try:
            # For expired keys, we send a special notification
            return email_service.send_api_key_revoked_notification(
                email=warning.user_email,
                username=warning.username,
                key_name=warning.key_name,
                key_id=warning.key_id,
                reason=f"API key expired on {warning.expires_at.strftime('%Y-%m-%d')}"
            )
        except Exception as e:
            print(f"Error sending expired notification: {e}")
            return False
    
    async def auto_disable_expired_keys(self, db: AsyncSession) -> List[str]:
        """
        Automatically disable API keys that have been expired beyond grace period.
        
        Args:
            db: Database session
            
        Returns:
            List of disabled API key IDs
        """
        now = datetime.utcnow()
        grace_period_end = now - timedelta(hours=self.policy.grace_period_hours)
        
        # Find keys that are expired beyond grace period
        query = select(APIKey).where(
            and_(
                APIKey.status == APIKeyStatus.active,
                APIKey.expires_at.isnot(None),
                APIKey.expires_at <= grace_period_end
            )
        )
        
        result = await db.execute(query)
        expired_keys = result.scalars().all()
        
        disabled_key_ids = []
        
        for api_key in expired_keys:
            try:
                # Update key status to revoked
                await db.execute(
                    update(APIKey)
                    .where(APIKey.id == api_key.id)
                    .values(
                        status=APIKeyStatus.revoked,
                        updated_at=now
                    )
                )
                
                disabled_key_ids.append(str(api_key.id))
                
                print(f"Auto-disabled expired API key: {api_key.key_id} (expired: {api_key.expires_at})")
                
            except Exception as e:
                print(f"Failed to auto-disable expired key {api_key.key_id}: {e}")
        
        if disabled_key_ids:
            await db.commit()
        
        return disabled_key_ids
    
    async def extend_key_expiration(
        self, 
        db: AsyncSession,
        api_key_id: str,
        additional_days: int,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Extend the expiration date of an API key.
        
        Args:
            db: Database session
            api_key_id: ID of the API key to extend
            additional_days: Number of days to add to current expiration
            user_id: Optional user ID for ownership verification
            
        Returns:
            True if extension was successful, False otherwise
        """
        if additional_days <= 0 or additional_days > self.policy.max_expiration_days:
            return False
        
        query = select(APIKey).where(APIKey.id == api_key_id)
        if user_id:
            query = query.where(APIKey.user_id == user_id)
        
        result = await db.execute(query)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return False
        
        # Calculate new expiration date
        current_expiry = api_key.expires_at or datetime.utcnow()
        new_expiry = current_expiry + timedelta(days=additional_days)
        
        # Check if new expiration exceeds policy limits
        max_future_date = datetime.utcnow() + timedelta(days=self.policy.max_expiration_days)
        if new_expiry > max_future_date:
            new_expiry = max_future_date
        
        try:
            await db.execute(
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(
                    expires_at=new_expiry,
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Failed to extend key expiration: {e}")
            return False
    
    async def get_expiration_stats(self, db: AsyncSession) -> Dict[str, int]:
        """
        Get statistics about key expiration across the system.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with expiration statistics
        """
        now = datetime.utcnow()
        
        # Count keys by expiration status
        queries = {
            "total_keys_with_expiry": select(APIKey).where(
                and_(
                    APIKey.status == APIKeyStatus.active,
                    APIKey.expires_at.isnot(None)
                )
            ),
            "expiring_30_days": select(APIKey).where(
                and_(
                    APIKey.status == APIKeyStatus.active,
                    APIKey.expires_at.isnot(None),
                    APIKey.expires_at <= now + timedelta(days=30),
                    APIKey.expires_at > now
                )
            ),
            "expiring_7_days": select(APIKey).where(
                and_(
                    APIKey.status == APIKeyStatus.active,
                    APIKey.expires_at.isnot(None),
                    APIKey.expires_at <= now + timedelta(days=7),
                    APIKey.expires_at > now
                )
            ),
            "expiring_1_day": select(APIKey).where(
                and_(
                    APIKey.status == APIKeyStatus.active,
                    APIKey.expires_at.isnot(None),
                    APIKey.expires_at <= now + timedelta(days=1),
                    APIKey.expires_at > now
                )
            ),
            "expired": select(APIKey).where(
                and_(
                    APIKey.status == APIKeyStatus.active,
                    APIKey.expires_at.isnot(None),
                    APIKey.expires_at <= now
                )
            ),
            "never_expire": select(APIKey).where(
                and_(
                    APIKey.status == APIKeyStatus.active,
                    APIKey.expires_at.is_(None)
                )
            )
        }
        
        stats = {}
        for stat_name, query in queries.items():
            result = await db.execute(query)
            count = len(result.scalars().all())
            stats[stat_name] = count
        
        return stats
    
    def get_policy_settings(self) -> ExpirationPolicy:
        """Get current expiration policy settings."""
        return self.policy
    
    def update_policy_settings(self, policy: ExpirationPolicy) -> bool:
        """Update expiration policy settings."""
        try:
            self.policy = policy
            return True
        except Exception as e:
            print(f"Failed to update policy settings: {e}")
            return False


# Global expiration manager instance
expiration_manager = ExpirationManager()


async def run_expiration_check():
    """
    Background task to check for expiring keys and send notifications.
    This function should be called periodically (e.g., daily).
    """
    try:
        print(f"Starting expiration check at {datetime.utcnow().isoformat()}")
        
        # Get database session
        db_generator = get_database()
        db = await db_generator.__anext__()
        
        try:
            # Check for expiring keys
            warnings = await expiration_manager.check_expiring_keys(db)
            print(f"Found {len(warnings)} keys requiring attention")
            
            # Send notifications
            if warnings:
                notification_counts = await expiration_manager.send_expiration_notifications(warnings)
                print(f"Notification results: {notification_counts}")
            
            # Auto-disable expired keys beyond grace period
            disabled_keys = await expiration_manager.auto_disable_expired_keys(db)
            if disabled_keys:
                print(f"Auto-disabled {len(disabled_keys)} expired keys: {disabled_keys}")
            
            # Get and log statistics
            stats = await expiration_manager.get_expiration_stats(db)
            print(f"Expiration statistics: {stats}")
            
        finally:
            # Close database session
            try:
                await db.close()
            except:
                pass
            
    except Exception as e:
        print(f"Error during expiration check: {e}")
        # Don't re-raise in background tasks
        import logging
        logging.error(f"Expiration check failed: {e}")
    
    print("Expiration check completed")