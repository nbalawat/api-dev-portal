"""
Email service for sending notifications and verification emails.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from pathlib import Path
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_tls = settings.smtp_tls
        self.from_email = settings.from_email
        
    def _send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email using SMTP."""
        # In test mode, skip actual email sending
        import os
        test_mode = (settings.app_env.lower() == "test" or 
                    os.getenv("ENVIRONMENT", "").lower() == "test" or 
                    os.getenv("TEST_MODE", "").lower() == "true")
        if test_mode:
            logger.info(f"Test mode: Skipping email send to {to_emails}")
            return True
            
        if not self.smtp_host or not self.smtp_user:
            logger.warning("SMTP not configured, email not sent")
            return False
            
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to_emails)
            
            if text_content:
                text_part = MIMEText(text_content, "plain")
                msg.attach(text_part)
                
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_tls:
                    server.starttls(context=context)
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_emails, msg.as_string())
                
            logger.info(f"Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_verification_email(self, email: str, username: str, token: str) -> bool:
        """Send email verification email."""
        verification_url = f"{settings.app_name}/auth/verify-email?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Email - {settings.app_name}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Welcome to {settings.app_name}!</h1>
                
                <p>Hi {username},</p>
                
                <p>Thank you for registering with {settings.app_name}. To complete your registration and verify your email address, please click the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Verify My Email Address
                    </a>
                </div>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #3498db;">{verification_url}</p>
                
                <p><strong>Important:</strong> This verification link will expire in 24 hours for security reasons.</p>
                
                <p>If you didn't register for an account with {settings.app_name}, please ignore this email.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated message from {settings.app_name}. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to {settings.app_name}!
        
        Hi {username},
        
        Thank you for registering with {settings.app_name}. To complete your registration and verify your email address, please visit this link:
        
        {verification_url}
        
        This verification link will expire in 24 hours for security reasons.
        
        If you didn't register for an account with {settings.app_name}, please ignore this email.
        """
        
        return self._send_email(
            to_emails=[email],
            subject=f"Verify Your Email - {settings.app_name}",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_password_reset_email(self, email: str, username: str, token: str) -> bool:
        """Send password reset email."""
        reset_url = f"{settings.app_name}/auth/reset-password?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Your Password - {settings.app_name}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #e74c3c;">Password Reset Request</h1>
                
                <p>Hi {username},</p>
                
                <p>We received a request to reset your password for your {settings.app_name} account. If you made this request, click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #e74c3c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Reset My Password
                    </a>
                </div>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #e74c3c;">{reset_url}</p>
                
                <p><strong>Important:</strong> This reset link will expire in 1 hour for security reasons.</p>
                
                <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged, and no further action is required.</p>
                
                <p>For security reasons, if you continue to receive these emails, please contact our support team.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated message from {settings.app_name}. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request - {settings.app_name}
        
        Hi {username},
        
        We received a request to reset your password for your {settings.app_name} account. If you made this request, visit this link to reset your password:
        
        {reset_url}
        
        This reset link will expire in 1 hour for security reasons.
        
        If you didn't request a password reset, please ignore this email. Your password will remain unchanged.
        """
        
        return self._send_email(
            to_emails=[email],
            subject=f"Reset Your Password - {settings.app_name}",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_welcome_email(self, email: str, username: str) -> bool:
        """Send welcome email after successful verification."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to {settings.app_name}!</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #27ae60;">Welcome to {settings.app_name}!</h1>
                
                <p>Hi {username},</p>
                
                <p>Your email has been successfully verified and your account is now active!</p>
                
                <p>You can now:</p>
                <ul>
                    <li>Access all {settings.app_name} features</li>
                    <li>Generate and manage API keys</li>
                    <li>Explore our comprehensive API documentation</li>
                    <li>Start building amazing applications</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.app_name}/dashboard" 
                       style="background-color: #27ae60; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Go to Dashboard
                    </a>
                </div>
                
                <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
                
                <p>Happy coding!</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated message from {settings.app_name}. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to {settings.app_name}!
        
        Hi {username},
        
        Your email has been successfully verified and your account is now active!
        
        You can now access all {settings.app_name} features, generate API keys, and start building amazing applications.
        
        Visit {settings.app_name}/dashboard to get started.
        
        Happy coding!
        """
        
        return self._send_email(
            to_emails=[email],
            subject=f"Welcome to {settings.app_name}!",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_api_key_created_notification(
        self, 
        email: str, 
        username: str, 
        key_name: str, 
        key_id: str,
        environment: str = "production",
        created_from_ip: Optional[str] = None
    ) -> bool:
        """Send notification when a new API key is created."""
        
        # Get current timestamp for the notification
        from datetime import datetime
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Security warning based on environment
        security_warning = ""
        if environment.lower() == "production":
            security_warning = """
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <strong>⚠️ Security Notice:</strong> This is a production API key. Handle with extreme care and never share it publicly.
            </div>
            """
        
        ip_info = f" from IP address {created_from_ip}" if created_from_ip else ""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>New API Key Created - {settings.app_name}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">🔑 New API Key Created</h1>
                
                <p>Hi {username},</p>
                
                <p>A new API key has been created for your {settings.app_name} account{ip_info}.</p>
                
                {security_warning}
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">Key Details:</h3>
                    <ul style="margin: 0;">
                        <li><strong>Key Name:</strong> {key_name}</li>
                        <li><strong>Key ID:</strong> {key_id}</li>
                        <li><strong>Environment:</strong> {environment.title()}</li>
                        <li><strong>Created:</strong> {created_at}</li>
                    </ul>
                </div>
                
                <div style="background-color: #e3f2fd; border: 1px solid #90caf9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1976d2;">🛡️ Security Recommendations:</h3>
                    <ul style="margin-bottom: 0;">
                        <li>Store your API key securely (use environment variables or a secure vault)</li>
                        <li>Never commit API keys to version control systems</li>
                        <li>Rotate your keys regularly (every 90 days recommended)</li>
                        <li>Monitor your key usage for any suspicious activity</li>
                        <li>Revoke keys immediately if you suspect they've been compromised</li>
                    </ul>
                </div>
                
                <p><strong>If you didn't create this API key,</strong> please:</p>
                <ol>
                    <li>Log into your account immediately</li>
                    <li>Revoke this API key</li>
                    <li>Change your account password</li>
                    <li>Contact our support team</li>
                </ol>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.app_name}/dashboard" 
                       style="background-color: #2c3e50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Manage API Keys
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated security notification from {settings.app_name}. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        New API Key Created - {settings.app_name}
        
        Hi {username},
        
        A new API key has been created for your {settings.app_name} account{ip_info}.
        
        Key Details:
        - Name: {key_name}
        - Key ID: {key_id}  
        - Environment: {environment.title()}
        - Created: {created_at}
        
        Security Recommendations:
        - Store your API key securely
        - Never commit API keys to version control
        - Rotate keys regularly (every 90 days)
        - Monitor usage for suspicious activity
        - Revoke keys if compromised
        
        If you didn't create this API key, please log into your account immediately and revoke it.
        
        Visit {settings.app_name}/dashboard to manage your API keys.
        """
        
        return self._send_email(
            to_emails=[email],
            subject=f"🔑 New API Key Created - {key_name}",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_api_key_revoked_notification(
        self, 
        email: str, 
        username: str, 
        key_name: str, 
        key_id: str,
        reason: Optional[str] = None,
        revoked_from_ip: Optional[str] = None
    ) -> bool:
        """Send notification when an API key is revoked."""
        
        from datetime import datetime
        revoked_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        reason_text = f" Reason: {reason}" if reason else ""
        ip_info = f" from IP address {revoked_from_ip}" if revoked_from_ip else ""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>API Key Revoked - {settings.app_name}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #e74c3c;">🔒 API Key Revoked</h1>
                
                <p>Hi {username},</p>
                
                <p>An API key has been revoked for your {settings.app_name} account{ip_info}.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">Revoked Key Details:</h3>
                    <ul style="margin: 0;">
                        <li><strong>Key Name:</strong> {key_name}</li>
                        <li><strong>Key ID:</strong> {key_id}</li>
                        <li><strong>Revoked:</strong> {revoked_at}</li>
                        {f"<li><strong>Reason:</strong> {reason}</li>" if reason else ""}
                    </ul>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>⚠️ Important:</strong> This API key is now permanently disabled and cannot be used to access your account or services.
                </div>
                
                <p>Any applications or services using this API key will no longer be able to authenticate. If this was an active key, you may need to:</p>
                <ul>
                    <li>Create a new API key to replace the revoked one</li>
                    <li>Update your applications with the new key</li>
                    <li>Test your integrations to ensure they're working properly</li>
                </ul>
                
                <p><strong>If you didn't revoke this API key,</strong> this could indicate unauthorized access to your account. Please:</p>
                <ol>
                    <li>Change your account password immediately</li>
                    <li>Review your account activity</li>
                    <li>Check for any other unauthorized changes</li>
                    <li>Contact our support team</li>
                </ol>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.app_name}/dashboard" 
                       style="background-color: #e74c3c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Review API Keys
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated security notification from {settings.app_name}. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        API Key Revoked - {settings.app_name}
        
        Hi {username},
        
        An API key has been revoked for your {settings.app_name} account{ip_info}.
        
        Revoked Key Details:
        - Name: {key_name}
        - Key ID: {key_id}
        - Revoked: {revoked_at}{reason_text}
        
        This API key is now permanently disabled. Any applications using this key will no longer be able to authenticate.
        
        If you didn't revoke this key, please change your password immediately and contact support.
        
        Visit {settings.app_name}/dashboard to review your API keys.
        """
        
        return self._send_email(
            to_emails=[email],
            subject=f"🔒 API Key Revoked - {key_name}",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_api_key_expiring_notification(
        self, 
        email: str, 
        username: str, 
        key_name: str, 
        key_id: str,
        expires_at: str,
        days_until_expiry: int
    ) -> bool:
        """Send notification when an API key is about to expire."""
        
        urgency_level = "critical" if days_until_expiry <= 7 else "warning" if days_until_expiry <= 30 else "info"
        urgency_color = "#e74c3c" if urgency_level == "critical" else "#f39c12" if urgency_level == "warning" else "#3498db"
        urgency_icon = "🚨" if urgency_level == "critical" else "⚠️" if urgency_level == "warning" else "ℹ️"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>API Key Expiring Soon - {settings.app_name}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: {urgency_color};">{urgency_icon} API Key Expiring Soon</h1>
                
                <p>Hi {username},</p>
                
                <p>One of your API keys is scheduled to expire in <strong>{days_until_expiry} day{"s" if days_until_expiry != 1 else ""}</strong>.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">Expiring Key Details:</h3>
                    <ul style="margin: 0;">
                        <li><strong>Key Name:</strong> {key_name}</li>
                        <li><strong>Key ID:</strong> {key_id}</li>
                        <li><strong>Expires:</strong> {expires_at}</li>
                        <li><strong>Days Remaining:</strong> {days_until_expiry}</li>
                    </ul>
                </div>
                
                <div style="background-color: #fef9e7; border: 1px solid #f1c40f; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #f39c12;">📋 Action Required:</h3>
                    <p style="margin-bottom: 0;">To avoid service interruption, please take one of the following actions before the expiration date:</p>
                    <ul style="margin-bottom: 0;">
                        <li><strong>Rotate the key:</strong> Create a new API key and update your applications</li>
                        <li><strong>Extend expiration:</strong> Update the expiration date if supported</li>
                        <li><strong>Plan for replacement:</strong> If this key is no longer needed, ensure services aren't depending on it</li>
                    </ul>
                </div>
                
                <p><strong>What happens when the key expires?</strong></p>
                <ul>
                    <li>The API key will be automatically disabled</li>
                    <li>Applications using this key will receive authentication errors</li>
                    <li>You'll need to create a new key to restore access</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.app_name}/dashboard" 
                       style="background-color: {urgency_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Manage API Keys
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated notification from {settings.app_name}. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        API Key Expiring Soon - {settings.app_name}
        
        Hi {username},
        
        One of your API keys is scheduled to expire in {days_until_expiry} day{"s" if days_until_expiry != 1 else ""}.
        
        Expiring Key Details:
        - Name: {key_name}
        - Key ID: {key_id}
        - Expires: {expires_at}
        - Days Remaining: {days_until_expiry}
        
        Action Required:
        - Rotate the key: Create a new API key and update your applications
        - Extend expiration: Update the expiration date if supported
        - Plan for replacement: Ensure services aren't depending on this key
        
        When the key expires, applications using it will receive authentication errors.
        
        Visit {settings.app_name}/dashboard to manage your API keys.
        """
        
        return self._send_email(
            to_emails=[email],
            subject=f"{urgency_icon} API Key Expiring in {days_until_expiry} Day{'s' if days_until_expiry != 1 else ''} - {key_name}",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_api_key_rotated_notification(
        self, 
        email: str, 
        username: str, 
        old_key_name: str, 
        old_key_id: str,
        new_key_name: str, 
        new_key_id: str,
        rotated_from_ip: Optional[str] = None
    ) -> bool:
        """Send notification when an API key is rotated."""
        
        from datetime import datetime
        rotated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        ip_info = f" from IP address {rotated_from_ip}" if rotated_from_ip else ""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>API Key Rotated - {settings.app_name}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #27ae60;">🔄 API Key Rotated</h1>
                
                <p>Hi {username},</p>
                
                <p>An API key has been rotated for your {settings.app_name} account{ip_info}.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">Rotation Details:</h3>
                    <div style="margin-bottom: 15px;">
                        <strong>Old Key (Revoked):</strong>
                        <ul style="margin: 5px 0;">
                            <li>Name: {old_key_name}</li>
                            <li>Key ID: {old_key_id}</li>
                        </ul>
                    </div>
                    <div>
                        <strong>New Key (Active):</strong>
                        <ul style="margin: 5px 0;">
                            <li>Name: {new_key_name}</li>
                            <li>Key ID: {new_key_id}</li>
                        </ul>
                    </div>
                    <p style="margin: 10px 0 0 0;"><strong>Rotated:</strong> {rotated_at}</p>
                </div>
                
                <div style="background-color: #e8f5e8; border: 1px solid #4caf50; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2e7d32;">✅ What This Means:</h3>
                    <ul style="margin-bottom: 0;">
                        <li>Your old API key has been revoked and can no longer be used</li>
                        <li>A new API key has been created with the same permissions</li>
                        <li>You'll need to update your applications to use the new key</li>
                        <li>The new key has been securely generated and is ready to use</li>
                    </ul>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">📋 Next Steps:</h3>
                    <ol style="margin-bottom: 0;">
                        <li>Copy your new API key from the dashboard (shown only once)</li>
                        <li>Update all applications and services to use the new key</li>
                        <li>Test your integrations to ensure they're working properly</li>
                        <li>Store the new key securely</li>
                    </ol>
                </div>
                
                <p><strong>If you didn't rotate this API key,</strong> please:</p>
                <ol>
                    <li>Log into your account immediately</li>
                    <li>Review all recent account activity</li>
                    <li>Change your account password</li>
                    <li>Contact our support team</li>
                </ol>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.app_name}/dashboard" 
                       style="background-color: #27ae60; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        View New API Key
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated security notification from {settings.app_name}. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        API Key Rotated - {settings.app_name}
        
        Hi {username},
        
        An API key has been rotated for your {settings.app_name} account{ip_info}.
        
        Rotation Details:
        - Old Key (Revoked): {old_key_name} ({old_key_id})
        - New Key (Active): {new_key_name} ({new_key_id})
        - Rotated: {rotated_at}
        
        What This Means:
        - Your old API key has been revoked
        - A new API key has been created with the same permissions
        - You'll need to update your applications to use the new key
        
        Next Steps:
        1. Copy your new API key from the dashboard
        2. Update all applications to use the new key
        3. Test your integrations
        4. Store the new key securely
        
        If you didn't rotate this key, please log in immediately and contact support.
        
        Visit {settings.app_name}/dashboard to view your new API key.
        """
        
        return self._send_email(
            to_emails=[email],
            subject=f"🔄 API Key Rotated - {new_key_name}",
            html_content=html_content,
            text_content=text_content
        )


# Global email service instance
email_service = EmailService()