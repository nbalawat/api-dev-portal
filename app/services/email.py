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


# Global email service instance
email_service = EmailService()