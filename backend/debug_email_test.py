#!/usr/bin/env python3
"""
Debug script to test email service configuration in test environment.
This script will help identify what's causing the EndOfStream error.
"""
import os
import sys
import traceback
import asyncio
from unittest.mock import Mock, patch

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_email_service_import():
    """Test if we can import the email service."""
    try:
        from app.services.email import EmailService, email_service
        print("✅ Email service import successful")
        return True
    except Exception as e:
        print(f"❌ Email service import failed: {e}")
        traceback.print_exc()
        return False

def test_config_import():
    """Test if we can import the config."""
    try:
        from app.core.config import Settings
        print("✅ Config import successful")
        return True
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        traceback.print_exc()
        return False

def test_email_service_with_no_smtp():
    """Test email service behavior with no SMTP configuration."""
    try:
        # Mock the settings to have no SMTP configuration
        with patch('app.services.email.settings') as mock_settings:
            mock_settings.smtp_host = None
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = None
            mock_settings.smtp_password = None
            mock_settings.smtp_tls = True
            mock_settings.from_email = "test@example.com"
            mock_settings.app_name = "Test App"
            
            from app.services.email import EmailService
            
            # Create email service instance
            email_service = EmailService()
            
            # Try to send a verification email
            result = email_service.send_verification_email(
                email="test@example.com",
                username="testuser",
                token="test_token_123"
            )
            
            print(f"✅ Email service with no SMTP config - Result: {result}")
            print("This should return False without crashing")
            return True
            
    except Exception as e:
        print(f"❌ Email service with no SMTP test failed: {e}")
        traceback.print_exc()
        return False

def test_email_service_with_invalid_smtp():
    """Test email service behavior with invalid SMTP configuration."""
    try:
        # Mock the settings to have invalid SMTP configuration
        with patch('app.services.email.settings') as mock_settings:
            mock_settings.smtp_host = "invalid-smtp-host.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "invalid_user"
            mock_settings.smtp_password = "invalid_password"
            mock_settings.smtp_tls = True
            mock_settings.from_email = "test@example.com"
            mock_settings.app_name = "Test App"
            
            from app.services.email import EmailService
            
            # Create email service instance
            email_service = EmailService()
            
            # Try to send a verification email - this should catch the exception
            result = email_service.send_verification_email(
                email="test@example.com",
                username="testuser",
                token="test_token_123"
            )
            
            print(f"✅ Email service with invalid SMTP config - Result: {result}")
            print("This should return False without crashing")
            return True
            
    except Exception as e:
        print(f"❌ Email service with invalid SMTP test failed: {e}")
        traceback.print_exc()
        return False

def test_fastapi_testclient_import():
    """Test if we can import FastAPI TestClient."""
    try:
        from fastapi.testclient import TestClient
        print("✅ FastAPI TestClient import successful")
        return True
    except Exception as e:
        print(f"❌ FastAPI TestClient import failed: {e}")
        traceback.print_exc()
        return False

def test_mock_registration_flow():
    """Test registration flow with mocked email service."""
    try:
        from unittest.mock import AsyncMock, patch
        from fastapi.testclient import TestClient
        
        # Mock the email service to prevent actual email sending
        with patch('app.services.email.email_service.send_verification_email') as mock_send:
            mock_send.return_value = True
            
            # Mock database operations
            with patch('app.dependencies.database.get_database') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value = mock_session
                
                # Mock database queries to return None (no existing user)
                mock_session.execute.return_value.scalar_one_or_none.return_value = None
                
                from app.main import app
                client = TestClient(app)
                
                test_user_data = {
                    "username": "testuser",
                    "email": "test@example.com",
                    "full_name": "Test User",
                    "password": "testpassword123",
                    "confirm_password": "testpassword123",
                    "role": "developer"
                }
                
                # This should not crash with EndOfStream error
                response = client.post("/auth/register", json=test_user_data)
                print(f"✅ Mock registration response status: {response.status_code}")
                print(f"Response content: {response.text}")
                
                return True
                
    except Exception as e:
        print(f"❌ Mock registration flow test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all debug tests."""
    print("🔍 Debug Email Service Configuration Issues")
    print("=" * 60)
    
    tests = [
        ("Config Import", test_config_import),
        ("Email Service Import", test_email_service_import),
        ("FastAPI TestClient Import", test_fastapi_testclient_import),
        ("Email Service - No SMTP", test_email_service_with_no_smtp),
        ("Email Service - Invalid SMTP", test_email_service_with_invalid_smtp),
        ("Mock Registration Flow", test_mock_registration_flow),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 40)
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n🔍 Potential Issues Identified:")
        print("1. Check if email service configuration is causing FastAPI TestClient to crash")
        print("2. Check if SMTP connection attempts are blocking the test client")
        print("3. Check if async/await handling in email service is correct")
        print("4. Consider mocking email service in test environment")

if __name__ == "__main__":
    main()