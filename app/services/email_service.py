"""Email service using Brevo SMTP"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
        self.smtp_port = int(os.getenv("BREVO_SMTP_PORT", "587"))
        self.smtp_user = os.getenv("BREVO_SMTP_USER")
        self.smtp_password = os.getenv("BREVO_SMTP_PASSWORD")
        self.from_email = os.getenv("BREVO_FROM_EMAIL", "noreply@aaris.com")
        self.from_name = os.getenv("BREVO_FROM_NAME", "AARIS")

    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email via Brevo SMTP"""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_otp(self, to_email: str, otp: str, purpose: str = "verification") -> bool:
        """Send OTP email"""
        subject = f"AARIS - Your {purpose.title()} Code"
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>AARIS Verification Code</h2>
            <p>Your {purpose} code is:</p>
            <h1 style="color: #4CAF50; font-size: 32px; letter-spacing: 5px;">{otp}</h1>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">AARIS - Academic Agentic Review Intelligence System</p>
        </body>
        </html>
        """
        return self.send_email(to_email, subject, html)

    def send_welcome(self, to_email: str, name: str) -> bool:
        """Send welcome email"""
        subject = "Welcome to AARIS"
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Welcome to AARIS, {name}!</h2>
            <p>Your account has been successfully created.</p>
            <p>You can now start submitting manuscripts for AI-powered academic review.</p>
            <p>Thank you for choosing AARIS!</p>
            <hr>
            <p style="color: #666; font-size: 12px;">AARIS - Academic Agentic Review Intelligence System</p>
        </body>
        </html>
        """
        return self.send_email(to_email, subject, html)


email_service = EmailService()
