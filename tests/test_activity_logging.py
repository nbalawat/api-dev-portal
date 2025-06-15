"""
Tests for Activity Logging System

Tests the comprehensive activity logging functionality including:
- Activity logging and storage
- Different activity types and severity levels
- Anomaly detection
- Activity retrieval and filtering
- Security event monitoring
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from app.services.activity_logging import (
    ActivityLogger, ActivityLogEntry, ActivityType, Severity,
    get_activity_logger, log_api_key_created, log_auth_attempt,
    log_rate_limit_event, log_security_event, log_admin_action
)


class TestActivityLogEntry:
    """Test activity log entry data structure."""
    
    def test_activity_log_entry_creation(self):
        """Test creating activity log entries."""
        entry = ActivityLogEntry(
            id="test_id",
            timestamp=datetime.utcnow(),
            activity_type=ActivityType.KEY_CREATED,
            severity=Severity.MEDIUM,
            api_key_id="test_key",
            user_id="test_user",
            source_ip="127.0.0.1",
            user_agent="Test Agent",
            endpoint="/api/v1/test",
            method="GET",
            status_code=200,
            response_time_ms=150.5,
            details={"test": "data"},
            tags=["test", "api_key"],
            session_id="session_123",
            request_id="request_456"
        )
        
        assert entry.id == "test_id"
        assert entry.activity_type == ActivityType.KEY_CREATED
        assert entry.severity == Severity.MEDIUM
        assert entry.api_key_id == "test_key"
        assert entry.details["test"] == "data"
        assert "test" in entry.tags


class TestActivityLogger:
    """Test the main activity logger functionality."""
    
    @pytest.mark.asyncio
    async def test_logger_initialization(self):
        """Test activity logger initialization."""
        logger = ActivityLogger()
        
        assert logger.log_buffer == []
        assert logger.buffer_size == 100
        assert logger.flush_interval == 30
        assert logger._flush_task is None
    
    @pytest.mark.asyncio
    async def test_log_activity(self):
        """Test basic activity logging."""
        logger = ActivityLogger()
        
        await logger.log_activity(
            activity_type=ActivityType.AUTH_SUCCESS,
            severity=Severity.LOW,
            api_key_id="test_key",
            user_id="test_user",
            source_ip="192.168.1.1",
            endpoint="/api/v1/profile",
            details={"login_method": "api_key"}
        )
        
        assert len(logger.log_buffer) == 1
        entry = logger.log_buffer[0]
        
        assert entry.activity_type == ActivityType.AUTH_SUCCESS
        assert entry.severity == Severity.LOW
        assert entry.api_key_id == "test_key"
        assert entry.source_ip == "192.168.1.1"
        assert entry.details["login_method"] == "api_key"
    
    @pytest.mark.asyncio
    async def test_log_key_creation(self):
        """Test API key creation logging."""
        logger = ActivityLogger()
        
        await logger.log_key_creation(
            api_key_id="new_key_123",
            user_id="user_456",
            key_name="Test API Key",
            scopes=["read", "write"],
            source_ip="10.0.0.1"
        )
        
        assert len(logger.log_buffer) == 1
        entry = logger.log_buffer[0]
        
        assert entry.activity_type == ActivityType.KEY_CREATED
        assert entry.severity == Severity.MEDIUM
        assert entry.api_key_id == "new_key_123"
        assert entry.user_id == "user_456"
        assert entry.details["key_name"] == "Test API Key"
        assert entry.details["scopes"] == ["read", "write"]
        assert "api_key" in entry.tags
        assert "creation" in entry.tags
    
    @pytest.mark.asyncio
    async def test_log_authentication_attempt(self):
        """Test authentication attempt logging."""
        logger = ActivityLogger()
        
        # Test successful authentication
        await logger.log_authentication_attempt(
            api_key_id="valid_key",
            success=True,
            source_ip="192.168.1.100",
            user_agent="MyApp/1.0",
            endpoint="/api/v1/data"
        )
        
        assert len(logger.log_buffer) == 1
        success_entry = logger.log_buffer[0]
        
        assert success_entry.activity_type == ActivityType.AUTH_SUCCESS
        assert success_entry.severity == Severity.LOW
        assert success_entry.details["success"] == True
        
        # Test failed authentication
        await logger.log_authentication_attempt(
            api_key_id=None,
            success=False,
            source_ip="192.168.1.100",
            failure_reason="Invalid API key"
        )
        
        assert len(logger.log_buffer) == 2
        failure_entry = logger.log_buffer[1]
        
        assert failure_entry.activity_type == ActivityType.AUTH_FAILED
        assert failure_entry.severity == Severity.MEDIUM
        assert failure_entry.details["success"] == False
        assert failure_entry.details["failure_reason"] == "Invalid API key"
    
    @pytest.mark.asyncio
    async def test_log_rate_limit_event(self):
        """Test rate limiting event logging."""
        logger = ActivityLogger()
        
        # Test rate limit exceeded
        await logger.log_rate_limit_event(
            api_key_id="test_key",
            event_type="exceeded",
            limit=100,
            current_usage=101,
            source_ip="192.168.1.1",
            endpoint="/api/v1/heavy-operation"
        )
        
        assert len(logger.log_buffer) == 1
        entry = logger.log_buffer[0]
        
        assert entry.activity_type == ActivityType.RATE_LIMIT_EXCEEDED
        assert entry.severity == Severity.HIGH
        assert entry.details["event_type"] == "exceeded"
        assert entry.details["limit"] == 100
        assert entry.details["current_usage"] == 101
        assert entry.details["usage_percentage"] == 101.0
        assert "rate_limiting" in entry.tags
    
    @pytest.mark.asyncio
    async def test_log_security_event(self):
        """Test security event logging."""
        logger = ActivityLogger()
        
        await logger.log_security_event(
            event_type="suspicious_activity",
            severity=Severity.HIGH,
            api_key_id="suspicious_key",
            source_ip="192.168.1.999",
            details={
                "reason": "Unusual request pattern",
                "requests_per_second": 50
            }
        )
        
        assert len(logger.log_buffer) == 1
        entry = logger.log_buffer[0]
        
        assert entry.activity_type == ActivityType.SUSPICIOUS_ACTIVITY
        assert entry.severity == Severity.HIGH
        assert entry.details["reason"] == "Unusual request pattern"
        assert "security" in entry.tags
    
    @pytest.mark.asyncio
    async def test_log_admin_action(self):
        """Test administrative action logging."""
        logger = ActivityLogger()
        
        await logger.log_admin_action(
            admin_user_id="admin_123",
            action="bulk_revoke",
            target_resource="api_keys",
            source_ip="10.0.0.5",
            details={
                "affected_keys": 5,
                "reason": "Security incident"
            }
        )
        
        assert len(logger.log_buffer) == 1
        entry = logger.log_buffer[0]
        
        assert entry.activity_type == ActivityType.ADMIN_ACCESS
        assert entry.severity == Severity.MEDIUM
        assert entry.user_id == "admin_123"
        assert entry.details["admin_action"] == "bulk_revoke"
        assert entry.details["target_resource"] == "api_keys"
        assert "admin" in entry.tags
    
    @pytest.mark.asyncio
    async def test_buffer_auto_flush(self):
        """Test automatic buffer flushing when critical events occur."""
        logger = ActivityLogger()
        
        # Mock the flush method
        logger._flush_logs = AsyncMock()
        
        # Log critical event (should trigger immediate flush)
        await logger.log_activity(
            activity_type=ActivityType.BRUTE_FORCE_DETECTED,
            severity=Severity.CRITICAL,
            api_key_id="attacked_key",
            details={"attempts": 100}
        )
        
        # Verify flush was called
        logger._flush_logs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_buffer_size_flush(self):
        """Test buffer flushing when size limit is reached."""
        logger = ActivityLogger()
        logger.buffer_size = 3  # Small buffer for testing
        
        # Mock the flush method
        logger._flush_logs = AsyncMock()
        
        # Add entries up to buffer size
        for i in range(3):
            await logger.log_activity(
                activity_type=ActivityType.AUTH_SUCCESS,
                severity=Severity.LOW,
                api_key_id=f"key_{i}"
            )
        
        # Verify flush was called when buffer filled
        logger._flush_logs.assert_called_once()


class TestActivityRetrieval:
    """Test activity log retrieval and filtering."""
    
    @pytest.mark.asyncio
    async def test_get_activity_logs_no_filter(self):
        """Test retrieving activity logs without filters."""
        logger = ActivityLogger()
        
        # Add some test activities
        activities = [
            (ActivityType.KEY_CREATED, "key1", "user1"),
            (ActivityType.AUTH_SUCCESS, "key1", "user1"),
            (ActivityType.RATE_LIMIT_HIT, "key2", "user2")
        ]
        
        for activity_type, api_key_id, user_id in activities:
            await logger.log_activity(
                activity_type=activity_type,
                api_key_id=api_key_id,
                user_id=user_id
            )
        
        # Retrieve all logs
        logs = await logger.get_activity_logs(limit=10)
        
        assert len(logs) == 3
        # Should be sorted by timestamp (most recent first)
        assert logs[0]['activity_type'] == ActivityType.RATE_LIMIT_HIT.value
        assert logs[1]['activity_type'] == ActivityType.AUTH_SUCCESS.value
        assert logs[2]['activity_type'] == ActivityType.KEY_CREATED.value
    
    @pytest.mark.asyncio
    async def test_get_activity_logs_with_filters(self):
        """Test retrieving activity logs with various filters."""
        logger = ActivityLogger()
        
        # Add test activities
        await logger.log_activity(
            activity_type=ActivityType.KEY_CREATED,
            api_key_id="key1",
            user_id="user1",
            severity=Severity.MEDIUM
        )
        
        await logger.log_activity(
            activity_type=ActivityType.AUTH_FAILED,
            api_key_id="key2",
            user_id="user2",
            severity=Severity.HIGH,
            source_ip="192.168.1.1"
        )
        
        await logger.log_activity(
            activity_type=ActivityType.RATE_LIMIT_EXCEEDED,
            api_key_id="key1",
            user_id="user1",
            severity=Severity.HIGH
        )
        
        # Filter by API key
        logs = await logger.get_activity_logs(api_key_id="key1")
        assert len(logs) == 2
        assert all(log['api_key_id'] == "key1" for log in logs)
        
        # Filter by user
        logs = await logger.get_activity_logs(user_id="user2")
        assert len(logs) == 1
        assert logs[0]['user_id'] == "user2"
        
        # Filter by activity type
        logs = await logger.get_activity_logs(
            activity_types=[ActivityType.AUTH_FAILED]
        )
        assert len(logs) == 1
        assert logs[0]['activity_type'] == ActivityType.AUTH_FAILED.value
        
        # Filter by severity
        logs = await logger.get_activity_logs(severity_filter=Severity.HIGH)
        assert len(logs) == 2
        assert all(log['severity'] == Severity.HIGH.value for log in logs)
        
        # Filter by source IP
        logs = await logger.get_activity_logs(source_ip="192.168.1.1")
        assert len(logs) == 1
        assert logs[0]['source_ip'] == "192.168.1.1"
    
    @pytest.mark.asyncio
    async def test_get_activity_summary(self):
        """Test activity summary generation."""
        logger = ActivityLogger()
        
        # Add various activities
        activities = [
            (ActivityType.KEY_CREATED, Severity.MEDIUM),
            (ActivityType.AUTH_SUCCESS, Severity.LOW),
            (ActivityType.AUTH_SUCCESS, Severity.LOW),
            (ActivityType.AUTH_FAILED, Severity.HIGH),
            (ActivityType.RATE_LIMIT_EXCEEDED, Severity.HIGH)
        ]
        
        for activity_type, severity in activities:
            await logger.log_activity(
                activity_type=activity_type,
                severity=severity,
                api_key_id="test_key",
                user_id="test_user"
            )
        
        # Get summary
        summary = await logger.get_activity_summary(
            api_key_id="test_key",
            hours=24
        )
        
        assert summary['summary']['total_activities'] == 5
        assert summary['summary']['activity_types'][ActivityType.AUTH_SUCCESS.value] == 2
        assert summary['summary']['severity_distribution'][Severity.LOW.value] == 2
        assert summary['summary']['severity_distribution'][Severity.HIGH.value] == 2
        assert len(summary['recent_activities']) <= 10
        assert len(summary['security_events']) >= 1  # High severity events


class TestAnomalyDetection:
    """Test anomaly detection functionality."""
    
    @pytest.mark.asyncio
    async def test_detect_repeated_auth_failures(self):
        """Test detection of repeated authentication failures."""
        logger = ActivityLogger()
        
        # Add many failed authentication attempts
        for i in range(15):  # More than threshold (10)
            await logger.log_activity(
                activity_type=ActivityType.AUTH_FAILED,
                api_key_id="suspicious_key",
                source_ip="192.168.1.100"
            )
        
        anomalies = await logger.detect_anomalies("suspicious_key", hours=24)
        
        # Should detect repeated failures
        failure_anomalies = [
            a for a in anomalies 
            if a["type"] == "repeated_auth_failures"
        ]
        assert len(failure_anomalies) > 0
        assert failure_anomalies[0]["count"] == 15
        assert failure_anomalies[0]["severity"] == "high"
    
    @pytest.mark.asyncio
    async def test_detect_multiple_source_ips(self):
        """Test detection of API key usage from multiple IPs."""
        logger = ActivityLogger()
        
        # Add activities from many different IPs
        ips = [f"192.168.1.{i}" for i in range(1, 8)]  # 7 IPs (more than threshold of 5)
        
        for ip in ips:
            await logger.log_activity(
                activity_type=ActivityType.AUTH_SUCCESS,
                api_key_id="traveling_key",
                source_ip=ip
            )
        
        anomalies = await logger.detect_anomalies("traveling_key", hours=24)
        
        # Should detect multiple IPs
        ip_anomalies = [
            a for a in anomalies 
            if a["type"] == "multiple_source_ips"
        ]
        assert len(ip_anomalies) > 0
        assert ip_anomalies[0]["count"] == 7
        assert ip_anomalies[0]["severity"] == "medium"
        assert len(ip_anomalies[0]["ips"]) == 7
    
    @pytest.mark.asyncio
    async def test_detect_frequent_rate_limiting(self):
        """Test detection of frequent rate limit violations."""
        logger = ActivityLogger()
        
        # Add many rate limit exceeded events
        for i in range(8):  # More than threshold (5)
            await logger.log_activity(
                activity_type=ActivityType.RATE_LIMIT_EXCEEDED,
                api_key_id="aggressive_key",
                severity=Severity.HIGH
            )
        
        anomalies = await logger.detect_anomalies("aggressive_key", hours=24)
        
        # Should detect frequent rate limiting
        rate_limit_anomalies = [
            a for a in anomalies 
            if a["type"] == "frequent_rate_limiting"
        ]
        assert len(rate_limit_anomalies) > 0
        assert rate_limit_anomalies[0]["count"] == 8
        assert rate_limit_anomalies[0]["severity"] == "medium"
    
    @pytest.mark.asyncio
    async def test_no_anomalies_for_normal_usage(self):
        """Test that normal usage doesn't trigger anomalies."""
        logger = ActivityLogger()
        
        # Add normal activities
        await logger.log_activity(
            activity_type=ActivityType.AUTH_SUCCESS,
            api_key_id="normal_key",
            source_ip="192.168.1.1"
        )
        
        await logger.log_activity(
            activity_type=ActivityType.ENDPOINT_ACCESSED,
            api_key_id="normal_key",
            source_ip="192.168.1.1"
        )
        
        anomalies = await logger.detect_anomalies("normal_key", hours=24)
        
        # Should not detect any anomalies
        assert len(anomalies) == 0


class TestConvenienceFunctions:
    """Test convenience functions for common logging operations."""
    
    @pytest.mark.asyncio
    async def test_log_api_key_created_function(self):
        """Test the convenience function for logging API key creation."""
        with patch('app.services.activity_logging.get_activity_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            
            await log_api_key_created(
                api_key_id="new_key",
                user_id="user123",
                key_name="Test Key",
                scopes=["read", "write"]
            )
            
            mock_logger.log_key_creation.assert_called_once_with(
                "new_key", "user123", "Test Key", ["read", "write"]
            )
    
    @pytest.mark.asyncio
    async def test_log_auth_attempt_function(self):
        """Test the convenience function for logging auth attempts."""
        with patch('app.services.activity_logging.get_activity_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            
            await log_auth_attempt(
                api_key_id="test_key",
                success=True,
                source_ip="127.0.0.1"
            )
            
            mock_logger.log_authentication_attempt.assert_called_once_with(
                "test_key", True, source_ip="127.0.0.1"
            )
    
    @pytest.mark.asyncio
    async def test_log_rate_limit_event_function(self):
        """Test the convenience function for logging rate limit events."""
        with patch('app.services.activity_logging.get_activity_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_get_logger.return_value = mock_logger
            
            await log_rate_limit_event(
                api_key_id="test_key",
                event_type="exceeded",
                limit=100,
                usage=105
            )
            
            mock_logger.log_rate_limit_event.assert_called_once_with(
                "test_key", "exceeded", 100, 105
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])