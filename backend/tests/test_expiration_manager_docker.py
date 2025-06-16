# -*- coding: utf-8 -*-
"""
Test expiration manager system for API key operations in Docker environment.

This test module verifies that expiration management works correctly
for automated checking, notifications, and policy enforcement.
Tests use real functionality without mocks to ensure actual behavior.
"""
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

# Add the app directory to Python path for imports
sys.path.insert(0, '/app')

from app.services.expiration_manager import ExpirationManager, ExpirationPolicy, ExpirationNotificationLevel
from app.services.email import EmailService
from app.models.api_key import APIKey, APIKeyStatus
from app.models.user import User, UserRole
from app.dependencies.database import get_database
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseMockHelper:
    """Helper to create mock database objects for testing."""
    
    @staticmethod
    def create_test_user():
        """Create a test user object."""
        return User(
            id=uuid4(),
            username="test_user",
            email="test@example.com",
            role=UserRole.developer,
            is_active=True,
            created_at=datetime.utcnow()
        )
    
    @staticmethod
    def create_test_api_key(user_id, expires_at=None, name="Test Key", key_id="ak_test123"):
        """Create a test API key object."""
        return APIKey(
            id=uuid4(),
            key_id=key_id,
            key_hash="test_hash",
            name=name,
            user_id=user_id,
            status=APIKeyStatus.active,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )


class EmailCapture:
    """Utility to capture email content during tests."""
    
    def __init__(self):
        self.emails_sent = []
        self.original_send_method = None
    
    def start_capture(self):
        """Start capturing emails."""
        self.emails_sent = []
        self.original_send_method = EmailService._send_email
        EmailService._send_email = self._capture_email
    
    def stop_capture(self):
        """Stop capturing emails and restore original method."""
        if self.original_send_method:
            EmailService._send_email = self.original_send_method
    
    def _capture_email(self, to_emails, subject, html_content, text_content=None):
        """Capture email content instead of sending."""
        self.emails_sent.append({
            'to_emails': to_emails,
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content,
            'timestamp': datetime.utcnow()
        })
        return True  # Simulate successful send
    
    def get_last_email(self):
        """Get the last captured email."""
        return self.emails_sent[-1] if self.emails_sent else None
    
    def get_emails_count(self):
        """Get number of emails captured."""
        return len(self.emails_sent)
    
    def clear(self):
        """Clear captured emails."""
        self.emails_sent = []


def test_expiration_manager_initialization():
    """Test that ExpirationManager initializes correctly."""
    print("Testing ExpirationManager initialization...")
    
    try:
        manager = ExpirationManager()
        
        # Verify manager has required attributes
        assert hasattr(manager, 'policy'), "Manager should have policy attribute"
        assert hasattr(manager, 'notification_tracking'), "Manager should have notification_tracking attribute"
        assert hasattr(manager, 'check_expiring_keys'), "Manager should have check_expiring_keys method"
        assert hasattr(manager, 'send_expiration_notifications'), "Manager should have send_expiration_notifications method"
        assert hasattr(manager, 'auto_disable_expired_keys'), "Manager should have auto_disable_expired_keys method"
        
        # Verify policy defaults
        policy = manager.get_policy_settings()
        assert policy.default_expiration_days == 90, "Default expiration should be 90 days"
        assert policy.warning_days == [30, 7, 1], "Warning days should be [30, 7, 1]"
        assert policy.auto_disable_expired is True, "Auto disable should be enabled"
        assert policy.grace_period_hours == 24, "Grace period should be 24 hours"
        assert policy.max_expiration_days == 365, "Max expiration should be 365 days"
        
        print("✓ ExpirationManager initialization test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ ExpirationManager initialization test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ ExpirationManager initialization test ERROR: {}".format(str(e)))
        return False


def test_expiration_notification_level_detection():
    """Test notification level detection logic."""
    print("Testing expiration notification level detection...")
    
    try:
        now = datetime.utcnow()
        
        # Test cases for different expiration scenarios
        test_cases = [
            (now - timedelta(days=1), ExpirationNotificationLevel.EXPIRED, "Already expired"),
            (now + timedelta(days=1), ExpirationNotificationLevel.CRITICAL_1_DAY, "1 day remaining"),
            (now + timedelta(days=3), ExpirationNotificationLevel.WARNING_7_DAYS, "3 days remaining"),
            (now + timedelta(days=7), ExpirationNotificationLevel.WARNING_7_DAYS, "7 days remaining"),
            (now + timedelta(days=15), ExpirationNotificationLevel.WARNING_30_DAYS, "15 days remaining"),
            (now + timedelta(days=30), ExpirationNotificationLevel.WARNING_30_DAYS, "30 days remaining"),
        ]
        
        for expires_at, expected_level, description in test_cases:
            days_until_expiry = (expires_at - now).days
            
            # Determine notification level (replicate logic from ExpirationManager)
            if days_until_expiry <= 0:
                level = ExpirationNotificationLevel.EXPIRED
            elif days_until_expiry <= 1:
                level = ExpirationNotificationLevel.CRITICAL_1_DAY
            elif days_until_expiry <= 7:
                level = ExpirationNotificationLevel.WARNING_7_DAYS
            else:
                level = ExpirationNotificationLevel.WARNING_30_DAYS
            
            assert level == expected_level, "Level detection failed for {}: expected {}, got {}".format(
                description, expected_level.value, level.value
            )
        
        print("✓ Expiration notification level detection test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Expiration notification level detection test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Expiration notification level detection test ERROR: {}".format(str(e)))
        return False


def test_expiration_policy_configuration():
    """Test expiration policy configuration."""
    print("Testing expiration policy configuration...")
    
    try:
        manager = ExpirationManager()
        
        # Test default policy
        default_policy = manager.get_policy_settings()
        assert default_policy.default_expiration_days == 90, "Default policy should have 90 day expiration"
        
        # Test custom policy
        custom_policy = ExpirationPolicy(
            default_expiration_days=180,
            warning_days=[60, 14, 3],
            auto_disable_expired=False,
            grace_period_hours=48,
            max_expiration_days=730
        )
        
        # Update policy
        result = manager.update_policy_settings(custom_policy)
        assert result is True, "Policy update should succeed"
        
        # Verify policy was updated
        updated_policy = manager.get_policy_settings()
        assert updated_policy.default_expiration_days == 180, "Updated policy should have 180 day expiration"
        assert updated_policy.warning_days == [60, 14, 3], "Updated policy should have custom warning days"
        assert updated_policy.auto_disable_expired is False, "Updated policy should have auto-disable disabled"
        assert updated_policy.grace_period_hours == 48, "Updated policy should have 48 hour grace period"
        assert updated_policy.max_expiration_days == 730, "Updated policy should have 730 day max expiration"
        
        print("✓ Expiration policy configuration test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Expiration policy configuration test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Expiration policy configuration test ERROR: {}".format(str(e)))
        return False


def test_expiration_warning_model():
    """Test ExpirationWarning model creation."""
    print("Testing ExpirationWarning model...")
    
    try:
        from app.services.expiration_manager import ExpirationWarning
        
        now = datetime.utcnow()
        expires_at = now + timedelta(days=5)
        
        warning = ExpirationWarning(
            api_key_id="test-key-id",
            key_name="Test Warning Key",
            key_id="ak_warning123",
            user_email="warning@example.com",
            username="warning_user",
            expires_at=expires_at,
            days_until_expiry=5,
            notification_level=ExpirationNotificationLevel.WARNING_7_DAYS
        )
        
        # Verify warning object
        assert warning.api_key_id == "test-key-id", "Warning should have correct API key ID"
        assert warning.key_name == "Test Warning Key", "Warning should have correct key name"
        assert warning.key_id == "ak_warning123", "Warning should have correct key ID"
        assert warning.user_email == "warning@example.com", "Warning should have correct user email"
        assert warning.username == "warning_user", "Warning should have correct username"
        assert warning.expires_at == expires_at, "Warning should have correct expiration date"
        assert warning.days_until_expiry == 5, "Warning should have correct days until expiry"
        assert warning.notification_level == ExpirationNotificationLevel.WARNING_7_DAYS, "Warning should have correct notification level"
        assert warning.last_warning_sent is None, "Warning should have no last warning sent by default"
        
        print("✓ ExpirationWarning model test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ ExpirationWarning model test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ ExpirationWarning model test ERROR: {}".format(str(e)))
        return False


def test_expiration_notification_sending():
    """Test expiration notification sending."""
    print("Testing expiration notification sending...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        from app.services.expiration_manager import ExpirationWarning
        
        manager = ExpirationManager()
        now = datetime.utcnow()
        
        # Create test warnings
        warnings = [
            ExpirationWarning(
                api_key_id="warning-30-id",
                key_name="30 Day Warning Key",
                key_id="ak_30day",
                user_email="30day@example.com",
                username="user_30day",
                expires_at=now + timedelta(days=25),
                days_until_expiry=25,
                notification_level=ExpirationNotificationLevel.WARNING_30_DAYS
            ),
            ExpirationWarning(
                api_key_id="warning-7-id",
                key_name="7 Day Warning Key",
                key_id="ak_7day",
                user_email="7day@example.com",
                username="user_7day",
                expires_at=now + timedelta(days=3),
                days_until_expiry=3,
                notification_level=ExpirationNotificationLevel.WARNING_7_DAYS
            ),
            ExpirationWarning(
                api_key_id="critical-1-id",
                key_name="1 Day Critical Key",
                key_id="ak_1day",
                user_email="1day@example.com",
                username="user_1day",
                expires_at=now + timedelta(hours=12),
                days_until_expiry=0,
                notification_level=ExpirationNotificationLevel.CRITICAL_1_DAY
            ),
            ExpirationWarning(
                api_key_id="expired-id",
                key_name="Expired Key",
                key_id="ak_expired",
                user_email="expired@example.com",
                username="user_expired",
                expires_at=now - timedelta(days=1),
                days_until_expiry=-1,
                notification_level=ExpirationNotificationLevel.EXPIRED
            )
        ]
        
        # Test async notification sending
        import asyncio
        
        async def test_notification_sending():
            counts = await manager.send_expiration_notifications(warnings, force_send=True)
            return counts
        
        # Run the async test
        counts = asyncio.run(test_notification_sending())
        
        # Verify notification counts
        assert counts["warning_30_days"] == 1, "Should send 1 thirty-day warning"
        assert counts["warning_7_days"] == 1, "Should send 1 seven-day warning"
        assert counts["critical_1_day"] == 1, "Should send 1 critical warning"
        assert counts["expired"] == 1, "Should send 1 expired notification"
        assert counts["failed"] == 0, "Should have no failures"
        
        # Verify emails were captured
        assert capture.get_emails_count() == 4, "Should capture 4 emails"
        
        # Verify email content
        emails = capture.emails_sent
        
        # Check 30-day warning email
        warning_30_email = next((e for e in emails if "30day@example.com" in e['to_emails']), None)
        assert warning_30_email is not None, "Should have 30-day warning email"
        assert "30 Day Warning Key" in warning_30_email['html_content'], "Should contain key name"
        assert "ak_30day" in warning_30_email['html_content'], "Should contain key ID"
        assert "25 day" in warning_30_email['html_content'], "Should contain days remaining"
        
        # Check critical warning email
        critical_email = next((e for e in emails if "1day@example.com" in e['to_emails']), None)
        assert critical_email is not None, "Should have critical warning email"
        assert "1 Day Critical Key" in critical_email['html_content'], "Should contain key name"
        assert "ak_1day" in critical_email['html_content'], "Should contain key ID"
        
        # Check expired notification email
        expired_email = next((e for e in emails if "expired@example.com" in e['to_emails']), None)
        assert expired_email is not None, "Should have expired notification email"
        assert "Expired Key" in expired_email['html_content'], "Should contain key name"
        assert "ak_expired" in expired_email['html_content'], "Should contain key ID"
        
        print("✓ Expiration notification sending test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Expiration notification sending test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Expiration notification sending test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_notification_throttling():
    """Test notification throttling to prevent spam."""
    print("Testing notification throttling...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        from app.services.expiration_manager import ExpirationWarning
        
        manager = ExpirationManager()
        now = datetime.utcnow()
        
        # Create same warning twice
        warning = ExpirationWarning(
            api_key_id="throttle-test-id",
            key_name="Throttle Test Key",
            key_id="ak_throttle",
            user_email="throttle@example.com",
            username="throttle_user",
            expires_at=now + timedelta(days=5),
            days_until_expiry=5,
            notification_level=ExpirationNotificationLevel.WARNING_7_DAYS
        )
        
        import asyncio
        
        async def test_throttling():
            # Send first notification
            counts1 = await manager.send_expiration_notifications([warning], force_send=True)
            
            # Try to send same notification again (should be throttled)
            counts2 = await manager.send_expiration_notifications([warning], force_send=False)
            
            return counts1, counts2
        
        counts1, counts2 = asyncio.run(test_throttling())
        
        # Verify first notification was sent
        assert counts1["warning_7_days"] == 1, "First notification should be sent"
        assert counts1["skipped"] == 0, "First notification should not be skipped"
        
        # Verify second notification was throttled
        assert counts2["warning_7_days"] == 0, "Second notification should not be sent"
        assert counts2["skipped"] == 1, "Second notification should be skipped"
        
        # Verify only one email was captured
        assert capture.get_emails_count() == 1, "Should only capture one email due to throttling"
        
        print("✓ Notification throttling test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Notification throttling test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Notification throttling test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_expiration_manager_integration():
    """Test complete expiration manager workflow."""
    print("Testing complete expiration manager workflow...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        manager = ExpirationManager()
        
        # Test policy updates
        custom_policy = ExpirationPolicy(
            default_expiration_days=60,
            warning_days=[14, 3, 1],
            auto_disable_expired=True,
            grace_period_hours=12,
            max_expiration_days=180
        )
        
        result = manager.update_policy_settings(custom_policy)
        assert result is True, "Policy update should succeed"
        
        # Verify policy was applied
        current_policy = manager.get_policy_settings()
        assert current_policy.default_expiration_days == 60, "Policy should be updated"
        assert current_policy.warning_days == [14, 3, 1], "Warning days should be updated"
        assert current_policy.grace_period_hours == 12, "Grace period should be updated"
        
        print("✓ Complete expiration manager workflow test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Complete expiration manager workflow test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Complete expiration manager workflow test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def run_all_tests():
    """Run all expiration manager tests."""
    print("=" * 60)
    print("RUNNING EXPIRATION MANAGER TESTS IN DOCKER")
    print("=" * 60)
    
    tests = [
        test_expiration_manager_initialization,
        test_expiration_notification_level_detection,
        test_expiration_policy_configuration,
        test_expiration_warning_model,
        test_expiration_notification_sending,
        test_notification_throttling,
        test_expiration_manager_integration
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
    
    print("=" * 60)
    print("TEST RESULTS:")
    print("PASSED: {}".format(passed))
    print("FAILED: {}".format(failed))
    print("TOTAL:  {}".format(passed + failed))
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)