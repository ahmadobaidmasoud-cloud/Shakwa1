import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending SMTP emails"""
    
    def __init__(
        self,
        smtp_host: str = settings.SMTP_HOST,
        smtp_port: int = settings.SMTP_PORT,
        smtp_user: str = settings.SMTP_USER,
        smtp_password: str = settings.SMTP_PASSWORD,
        from_name: str = settings.SMTP_FROM_NAME,
        from_email: str = settings.SMTP_FROM_EMAIL,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_name = from_name
        self.from_email = from_email

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send email via SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            cc: List of CC emails (optional)
            bcc: List of BCC emails (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            if cc:
                message["Cc"] = ", ".join(cc)
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Prepare recipients list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, recipients, message.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_welcome_email(
        self,
        to_email: str,
        tenant_name: str,
        first_name: str,
        temporary_password: str,
        login_url: str = None,
    ) -> bool:
        """
        Send welcome email to tenant admin
        
        Args:
            to_email: Admin email address
            tenant_name: Organization name
            first_name: Admin first name
            temporary_password: Temporary password for first login
            login_url: Login URL (optional)
            
        Returns:
            True if email sent successfully
        """
        if not login_url:
            login_url = f"{settings.FRONTEND_URL}/login"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #667eea;">Welcome to Shakwa!</h2>
                    
                    <p>Hi {first_name},</p>
                    
                    <p>Your tenant account for <strong>{tenant_name}</strong> has been successfully created. You are now the administrator for this organization.</p>
                    
                    <h3 style="color: #667eea; margin-top: 25px;">Login Details</h3>
                    <p>
                        <strong>Email:</strong> {to_email}<br>
                        <strong>Temporary Password:</strong> <code style="background-color: #f0f0f0; padding: 5px 10px; border-radius: 3px;">{temporary_password}</code>
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{login_url}" style="background-color: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            Log In to Dashboard
                        </a>
                    </div>
                    
                    <h3 style="color: #667eea; margin-top: 25px;">Next Steps</h3>
                    <ol>
                        <li>Log in to your dashboard using the credentials above</li>
                        <li>Set up your tenant organization</li>
                        <li>Add team members to collaborate</li>
                    </ol>
                    
                    <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 12px;">
                        If you have any questions, please contact our support team.
                    </p>
                    
                    <p style="color: #666; font-size: 12px;">
                        Best regards,<br>
                        <strong>Shakwa Team</strong>
                    </p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(
            to_email=to_email,
            subject=f"Welcome to Shakwa - Your {tenant_name} Account is Ready",
            html_content=html_content,
        )


# Create a singleton instance
email_service = EmailService()
