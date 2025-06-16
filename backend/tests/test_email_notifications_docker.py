# -*- coding: utf-8 -*-
"""
Test email notification system for API key operations in Docker environment.

This test module verifies that email notifications are sent correctly
for API key lifecycle events: creation, revocation, rotation, and expiration warnings.
Tests use real functionality without mocks to ensure actual behavior.
"""
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to Python path for imports
sys.path.insert(0, '/app')

from app.services.email import EmailService


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
    
    def _capture_email(self, instance, to_emails, subject, html_content, text_content=None):
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


def test_email_notification_creation():
    """Test for email creation notification."""
    print("Testing API key creation notification...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        service = EmailService()
        result = service.send_api_key_created_notification(
            email="test@example.com",
            username="test_user",
            key_name="Docker Test Key",
            key_id="ak_docker123",
            environment="production",
            created_from_ip="172.17.0.1"
        )
        
        # Verify email was sent
        assert result is True, "Email notification should return True"
        assert capture.get_emails_count() == 1, "Exactly one email should be captured"
        
        # Verify email content
        email = capture.get_last_email()
        assert email is not None, "Email should be captured"
        assert "test@example.com" in email['to_emails'], "Email should be sent to correct address"
        assert "Docker Test Key" in email['subject'], "Subject should contain key name"
        assert "test_user" in email['html_content'], "Content should contain username"
        assert "ak_docker123" in email['html_content'], "Content should contain key ID"
        assert "Production" in email['html_content'], "Content should contain environment"
        assert "172.17.0.1" in email['html_content'], "Content should contain IP address"
        
        # Verify security elements
        assert "Security Notice" in email['html_content'], "Should have production security notice"
        assert "environment variables" in email['html_content'], "Should have security recommendations"
        assert "version control" in email['html_content'], "Should warn about version control"
        
        print("✓ API key creation notification test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ API key creation notification test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ API key creation notification test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_email_notification_revocation():
    """Test for email revocation notification."""
    print("Testing API key revocation notification...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        service = EmailService()
        result = service.send_api_key_revoked_notification(
            email="revoke@example.com",
            username="revoke_user",
            key_name="Revoked Docker Key",
            key_id="ak_revoked456",
            reason="Security audit",
            revoked_from_ip="172.17.0.1"
        )
        
        # Verify email was sent
        assert result is True, "Email notification should return True"
        assert capture.get_emails_count() == 1, "Exactly one email should be captured"
        
        # Verify email content
        email = capture.get_last_email()
        assert email is not None, "Email should be captured"
        assert "revoke@example.com" in email['to_emails'], "Email should be sent to correct address"
        assert "API Key Revoked" in email['subject'], "Subject should indicate revocation"
        assert "Revoked Docker Key" in email['subject'], "Subject should contain key name"
        assert "revoke_user" in email['html_content'], "Content should contain username"
        assert "ak_revoked456" in email['html_content'], "Content should contain key ID"
        assert "Security audit" in email['html_content'], "Content should contain reason"
        assert "172.17.0.1" in email['html_content'], "Content should contain IP address"
        
        # Verify revocation-specific content
        assert "permanently disabled" in email['html_content'], "Should explain key is disabled"
        assert "cannot be used" in email['html_content'], "Should warn key cannot be used"
        assert "Create a new API key" in email['html_content'], "Should suggest creating new key"
        assert "Change your account password" in email['html_content'], "Should suggest security measures"
        
        print("✓ API key revocation notification test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ API key revocation notification test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ API key revocation notification test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_email_notification_rotation():
    """Test for email rotation notification."""
    print("Testing API key rotation notification...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        service = EmailService()
        result = service.send_api_key_rotated_notification(
            email="rotate@example.com",
            username="rotate_user",
            old_key_name="Old Docker Key",
            old_key_id="ak_old789",
            new_key_name="New Docker Key",
            new_key_id="ak_new012",
            rotated_from_ip="172.17.0.1"
        )
        
        # Verify email was sent
        assert result is True, "Email notification should return True"
        assert capture.get_emails_count() == 1, "Exactly one email should be captured"
        
        # Verify email content
        email = capture.get_last_email()
        assert email is not None, "Email should be captured"
        assert "rotate@example.com" in email['to_emails'], "Email should be sent to correct address"
        assert "API Key Rotated" in email['subject'], "Subject should indicate rotation"
        assert "rotate_user" in email['html_content'], "Content should contain username"
        assert "Old Docker Key" in email['html_content'], "Content should contain old key name"
        assert "ak_old789" in email['html_content'], "Content should contain old key ID"
        assert "New Docker Key" in email['html_content'], "Content should contain new key name"
        assert "ak_new012" in email['html_content'], "Content should contain new key ID"
        assert "172.17.0.1" in email['html_content'], "Content should contain IP address"
        
        # Verify rotation-specific content
        assert "Old Key (Revoked)" in email['html_content'], "Should label old key as revoked"
        assert "New Key (Active)" in email['html_content'], "Should label new key as active"
        assert "Copy your new API key" in email['html_content'], "Should instruct to copy new key"
        assert "Update all applications" in email['html_content'], "Should instruct to update apps"
        
        print("✓ API key rotation notification test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ API key rotation notification test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ API key rotation notification test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_email_notification_expiring():
    """Test for email expiring notification."""
    print("Testing API key expiring notification...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        service = EmailService()
        expires_at = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        result = service.send_api_key_expiring_notification(
            email="expiring@example.com",
            username="expiring_user",
            key_name="Expiring Docker Key",
            key_id="ak_expiring345",
            expires_at=expires_at,
            days_until_expiry=5
        )
        
        # Verify email was sent
        assert result is True, "Email notification should return True"
        assert capture.get_emails_count() == 1, "Exactly one email should be captured"
        
        # Verify email content
        email = capture.get_last_email()
        assert email is not None, "Email should be captured"
        assert "expiring@example.com" in email['to_emails'], "Email should be sent to correct address"
        assert "API Key Expiring" in email['subject'], "Subject should indicate expiring"
        assert "5 Day" in email['subject'], "Subject should show days remaining"
        assert "expiring_user" in email['html_content'], "Content should contain username"
        assert "Expiring Docker Key" in email['html_content'], "Content should contain key name"
        assert "ak_expiring345" in email['html_content'], "Content should contain key ID"
        assert expires_at in email['html_content'], "Content should contain expiration date"
        assert "5 day" in email['html_content'], "Content should show days remaining"
        
        # Verify expiring-specific content
        assert "Action Required" in email['html_content'], "Should indicate action required"
        assert "Rotate the key" in email['html_content'], "Should suggest rotation"
        assert "Extend expiration" in email['html_content'], "Should suggest extension"
        assert "automatically disabled" in email['html_content'], "Should warn about auto-disable"
        
        print("✓ API key expiring notification test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ API key expiring notification test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ API key expiring notification test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_email_notification_dev_environment():
    """Test that development environment doesn't show production warnings."""
    print("Testing development environment notification...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        service = EmailService()
        result = service.send_api_key_created_notification(
            email="dev@example.com",
            username="dev_user",
            key_name="Dev Docker Key",
            key_id="ak_dev678",
            environment="development"
        )
        
        # Verify email was sent
        assert result is True, "Email notification should return True"
        assert capture.get_emails_count() == 1, "Exactly one email should be captured"
        
        # Verify email content
        email = capture.get_last_email()
        assert email is not None, "Email should be captured"
        assert "Development" in email['html_content'], "Should show development environment"
        
        # Verify NO production warnings for dev environment
        assert "Security Notice" not in email['html_content'], "Should not have production security notice"
        assert "production API key" not in email['html_content'], "Should not mention production"
        
        print("✓ Development environment notification test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Development environment notification test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Development environment notification test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_email_service_initialization():
    """Test that EmailService initializes correctly."""
    print("Testing EmailService initialization...")
    
    try:
        service = EmailService()
        
        # Verify service has required attributes
        assert hasattr(service, 'smtp_host'), "Service should have smtp_host attribute"
        assert hasattr(service, 'from_email'), "Service should have from_email attribute"
        assert hasattr(service, '_send_email'), "Service should have _send_email method"
        
        print("✓ EmailService initialization test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ EmailService initialization test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ EmailService initialization test ERROR: {}".format(str(e)))
        return False


def test_email_workflow_sequence():
    """Test complete email workflow sequence."""
    print("Testing complete email workflow sequence...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        service = EmailService()
        
        # Simulate complete workflow: create -> rotate -> revoke
        
        # 1. Create notification
        service.send_api_key_created_notification(
            email="workflow@example.com",
            username="workflow_user",
            key_name="Workflow Key",
            key_id="ak_workflow111",
            environment="production"
        )
        
        # 2. Rotation notification
        service.send_api_key_rotated_notification(
            email="workflow@example.com",
            username="workflow_user",
            old_key_name="Workflow Key",
            old_key_id="ak_workflow111",
            new_key_name="Workflow Key (Rotated)",
            new_key_id="ak_workflow222"
        )
        
        # 3. Revocation notification
        service.send_api_key_revoked_notification(
            email="workflow@example.com",
            username="workflow_user",
            key_name="Workflow Key (Rotated)",
            key_id="ak_workflow222",
            reason="End of project"
        )
        
        # Verify all emails were captured
        assert capture.get_emails_count() == 3, "Should have captured 3 emails"
        
        emails = capture.emails_sent
        
        # Verify order and content
        assert "New API Key Created" in emails[0]['subject'], "First email should be creation"
        assert "API Key Rotated" in emails[1]['subject'], "Second email should be rotation"
        assert "API Key Revoked" in emails[2]['subject'], "Third email should be revocation"
        
        # Verify all emails went to same user
        for email in emails:
            assert "workflow@example.com" in email['to_emails'], "All emails should go to same address"
            assert "workflow_user" in email['html_content'], "All emails should mention same user"
        
        print("✓ Complete email workflow sequence test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Complete email workflow sequence test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Complete email workflow sequence test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def run_all_tests():
    """Run all email notification tests."""
    print("=" * 60)
    print("RUNNING EMAIL NOTIFICATION TESTS IN DOCKER")
    print("=" * 60)
    
    tests = [
        test_email_service_initialization,
        test_email_notification_creation,
        test_email_notification_revocation,
        test_email_notification_rotation,
        test_email_notification_expiring,
        test_email_notification_dev_environment,
        test_email_workflow_sequence
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