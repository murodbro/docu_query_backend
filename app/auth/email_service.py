"""Email service using Resend API for sending verification emails."""

import os
import secrets
from datetime import datetime, timedelta

import resend

# Initialize Resend with API key
resend.api_key = os.getenv("RESEND_API_KEY", "")

# Configuration
VERIFICATION_TOKEN_EXPIRE_HOURS = 24
FROM_EMAIL = "DocuQuery <noreply@updates.murodbro.uz>"  # Verified domain
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def generate_verification_token() -> str:
    """Generate a secure random verification token."""
    return secrets.token_urlsafe(32)


def get_verification_token_expiry() -> datetime:
    """Get the expiry time for verification token."""
    return datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)


def send_verification_email(email: str, name: str, token: str) -> bool:
    """
    Send email verification link to user.

    Args:
        email: User's email address
        name: User's name
        token: Verification token

    Returns:
        True if email was sent successfully, False otherwise
    """
    verification_url = f"{FRONTEND_URL}/verify-email?token={token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">DocuQuery</h1>
        </div>
        <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Welcome, {name}! 👋</h2>
            <p>Thank you for signing up for DocuQuery. To complete your registration, please verify your email address by clicking the button below:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
            <p style="background: #f5f5f5; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px; color: #666;">{verification_url}</p>
            <p style="color: #999; font-size: 12px; margin-top: 30px;">This link will expire in {VERIFICATION_TOKEN_EXPIRE_HOURS} hours. If you didn't create an account, you can safely ignore this email.</p>
        </div>
        <p style="text-align: center; color: #999; font-size: 12px; margin-top: 20px;">© 2024 DocuQuery. All rights reserved.</p>
    </body>
    </html>
    """

    try:
        params = {
            "from": FROM_EMAIL,
            "to": [email],
            "subject": "Verify your DocuQuery account",
            "html": html_content,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send verification email: {e}")
        return False


def send_password_reset_email(email: str, name: str, token: str) -> bool:
    """
    Send password reset link to user.

    Args:
        email: User's email address
        name: User's name
        token: Reset token

    Returns:
        True if email was sent successfully, False otherwise
    """
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">DocuQuery</h1>
        </div>
        <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Password Reset Request</h2>
            <p>Hi {name}, we received a request to reset your password. Click the button below to create a new password:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                    Reset Password
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
            <p style="background: #f5f5f5; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px; color: #666;">{reset_url}</p>
            <p style="color: #999; font-size: 12px; margin-top: 30px;">This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email.</p>
        </div>
        <p style="text-align: center; color: #999; font-size: 12px; margin-top: 20px;">© 2024 DocuQuery. All rights reserved.</p>
    </body>
    </html>
    """

    try:
        params = {
            "from": FROM_EMAIL,
            "to": [email],
            "subject": "Reset your DocuQuery password",
            "html": html_content,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send password reset email: {e}")
        return False
