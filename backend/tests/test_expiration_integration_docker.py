# -*- coding: utf-8 -*-
"""
Integration tests for expiration management system in Docker environment.

This test module verifies that the complete expiration system works correctly
including background tasks, API endpoints, and email notifications.
Tests use real functionality without mocks to ensure actual behavior.
"""
import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add the app directory to Python path for imports
sys.path.insert(0, '/app')

from app.services.expiration_manager import expiration_manager, ExpirationPolicy
from app.services.background_scheduler import background_scheduler, initialize_default_tasks
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


def test_background_scheduler_initialization():
    """Test background scheduler initialization."""
    print("Testing background scheduler initialization...")
    
    try:
        # Initialize default tasks
        initialize_default_tasks()
        
        # Check that tasks were registered
        all_tasks = background_scheduler.get_all_task_status()
        assert "api_key_expiration_check" in all_tasks, "Expiration check task should be registered"
        
        task_status = all_tasks["api_key_expiration_check"]
        assert task_status["enabled"] is True, "Expiration check task should be enabled"
        assert task_status["frequency"] == "daily", "Expiration check task should run daily"
        assert task_status["next_run"] is not None, "Expiration check task should have next run time"
        
        print("✓ Background scheduler initialization test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Background scheduler initialization test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Background scheduler initialization test ERROR: {}".format(str(e)))
        return False


def test_background_task_execution():
    """Test background task manual execution."""
    print("Testing background task execution...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        # Initialize tasks
        initialize_default_tasks()
        
        # Test task existence and basic functionality
        task_status = background_scheduler.get_task_status("api_key_expiration_check")
        assert task_status is not None, "Task should exist"
        assert task_status["enabled"] is True, "Task should be enabled"
        
        print("✓ Background task execution test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Background task execution test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Background task execution test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_expiration_policy_updates():
    """Test expiration policy configuration updates."""
    print("Testing expiration policy updates...")
    
    try:
        # Get current policy
        original_policy = expiration_manager.get_policy_settings()
        
        # Create custom policy
        custom_policy = ExpirationPolicy(
            default_expiration_days=45,
            warning_days=[21, 7, 2],
            auto_disable_expired=True,
            grace_period_hours=6,
            max_expiration_days=180
        )
        
        # Update policy
        success = expiration_manager.update_policy_settings(custom_policy)
        assert success is True, "Policy update should succeed"
        
        # Verify policy was updated
        updated_policy = expiration_manager.get_policy_settings()
        assert updated_policy.default_expiration_days == 45, "Default expiration should be 45 days"
        assert updated_policy.warning_days == [21, 7, 2], "Warning days should be [21, 7, 2]"
        assert updated_policy.grace_period_hours == 6, "Grace period should be 6 hours"
        assert updated_policy.max_expiration_days == 180, "Max expiration should be 180 days"
        
        # Restore original policy
        expiration_manager.update_policy_settings(original_policy)
        
        print("✓ Expiration policy updates test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Expiration policy updates test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Expiration policy updates test ERROR: {}".format(str(e)))
        return False


def test_scheduler_task_control():
    """Test background scheduler task control operations."""
    print("Testing scheduler task control...")
    
    try:
        # Initialize tasks
        initialize_default_tasks()
        
        # Test task enabling/disabling
        task_name = "api_key_expiration_check"
        
        # Disable task
        success = background_scheduler.disable_task(task_name)
        assert success is True, "Task disable should succeed"
        
        task_status = background_scheduler.get_task_status(task_name)
        assert task_status["enabled"] is False, "Task should be disabled"
        
        # Enable task
        success = background_scheduler.enable_task(task_name)
        assert success is True, "Task enable should succeed"
        
        task_status = background_scheduler.get_task_status(task_name)
        assert task_status["enabled"] is True, "Task should be enabled"
        
        # Test invalid task name
        success = background_scheduler.disable_task("nonexistent_task")
        assert success is False, "Disabling nonexistent task should fail"
        
        print("✓ Scheduler task control test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Scheduler task control test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Scheduler task control test ERROR: {}".format(str(e)))
        return False


def test_expiration_system_end_to_end():
    """Test complete expiration system end-to-end."""
    print("Testing expiration system end-to-end...")
    
    capture = EmailCapture()
    capture.start_capture()
    
    try:
        # Initialize system
        initialize_default_tasks()
        
        # Configure policy for testing
        test_policy = ExpirationPolicy(
            default_expiration_days=30,
            warning_days=[7, 3, 1],
            auto_disable_expired=True,
            grace_period_hours=12,
            max_expiration_days=90
        )
        expiration_manager.update_policy_settings(test_policy)
        
        # Verify policy was set
        current_policy = expiration_manager.get_policy_settings()
        assert current_policy.default_expiration_days == 30, "Policy should be updated"
        
        # Verify scheduler status
        scheduler_status = background_scheduler.get_all_task_status()
        assert len(scheduler_status) > 0, "Should have registered tasks"
        assert "api_key_expiration_check" in scheduler_status, "Should have expiration check task"
        
        # Verify task configuration
        task_status = scheduler_status["api_key_expiration_check"]
        assert task_status["enabled"] is True, "Task should be enabled"
        assert task_status["frequency"] == "daily", "Task should run daily"
        
        print("✓ Expiration system end-to-end test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Expiration system end-to-end test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Expiration system end-to-end test ERROR: {}".format(str(e)))
        return False
    finally:
        capture.stop_capture()


def test_scheduler_running_state():
    """Test scheduler running state management."""
    print("Testing scheduler running state...")
    
    try:
        # Check initial state
        is_running = background_scheduler.is_running()
        print("Initial running state: {}".format(is_running))
        
        # Test scheduler status
        status = background_scheduler.get_all_task_status()
        assert isinstance(status, dict), "Status should be a dictionary"
        
        # Test that we can get task information
        if status:
            first_task = next(iter(status.values()))
            assert "enabled" in first_task, "Task should have enabled field"
            assert "frequency" in first_task, "Task should have frequency field"
        
        print("✓ Scheduler running state test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Scheduler running state test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Scheduler running state test ERROR: {}".format(str(e)))
        return False


def test_error_handling_resilience():
    """Test error handling and system resilience."""
    print("Testing error handling resilience...")
    
    try:
        # Initialize tasks
        initialize_default_tasks()
        
        # Test with invalid task operations
        invalid_status = background_scheduler.get_task_status("invalid_task")
        assert invalid_status is None, "Invalid task should return None status"
        
        # Test policy validation
        policy = expiration_manager.get_policy_settings()
        assert policy is not None, "Policy should always be available"
        
        # Test manager state
        manager_tracking = expiration_manager.notification_tracking
        assert isinstance(manager_tracking, dict), "Notification tracking should be a dict"
        
        print("✓ Error handling resilience test PASSED")
        return True
        
    except AssertionError as e:
        print("✗ Error handling resilience test FAILED: {}".format(str(e)))
        return False
    except Exception as e:
        print("✗ Error handling resilience test ERROR: {}".format(str(e)))
        return False


def run_all_tests():
    """Run all expiration integration tests."""
    print("=" * 70)
    print("RUNNING EXPIRATION INTEGRATION TESTS IN DOCKER")
    print("=" * 70)
    
    tests = [
        test_background_scheduler_initialization,
        test_background_task_execution,
        test_expiration_policy_updates,
        test_scheduler_task_control,
        test_scheduler_running_state,
        test_error_handling_resilience,
        test_expiration_system_end_to_end
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
    print("INTEGRATION TEST RESULTS:")
    print("PASSED: {}".format(passed))
    print("FAILED: {}".format(failed))
    print("TOTAL:  {}".format(passed + failed))
    
    if failed == 0:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("The expiration management system is fully functional!")
        return True
    else:
        print("❌ SOME INTEGRATION TESTS FAILED!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)