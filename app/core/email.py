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


    def send_ticket_confirmation_email(
        self,
        to_email: str,
        first_name: str,
        ticket_id: str,
        tenant_slug: str,
        ticket_url: str,
    ) -> bool:
        """
        Send a ticket submission confirmation email to the person who submitted it.

        Args:
            to_email: Submitter email address
            first_name: Submitter's first name
            ticket_id: The UUID of the newly created ticket
            tenant_slug: Tenant slug (for display)
            ticket_url: Full URL to the public ticket tracker page

        Returns:
            True if email sent successfully
        """
        short_id = str(ticket_id).split("-")[0].upper()

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f7;">
                <div style="max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px 40px;">
                        <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: -0.3px;">
                            Ticket Received ✓
                        </h1>
                        <p style="margin: 6px 0 0; color: rgba(255,255,255,0.85); font-size: 14px;">
                            We've got your request and will be in touch soon.
                        </p>
                    </div>

                    <!-- Body -->
                    <div style="padding: 32px 40px;">
                        <p style="margin: 0 0 16px;">Hi <strong>{first_name}</strong>,</p>

                        <p style="margin: 0 0 24px; color: #555;">
                            Your ticket has been successfully submitted. Our team will review it and get back to you as soon as possible.
                        </p>

                        <!-- Ticket Info Box -->
                        <div style="background: #f8f8fc; border-left: 4px solid #667eea; border-radius: 4px; padding: 16px 20px; margin-bottom: 28px;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                                <tr>
                                    <td style="padding: 4px 0; color: #888; width: 120px;">Ticket ID</td>
                                    <td style="padding: 4px 0; font-weight: 600; color: #333;">#{short_id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 4px 0; color: #888;">Status</td>
                                    <td style="padding: 4px 0;">
                                        <span style="display: inline-block; background: #eef0ff; color: #667eea; font-size: 12px; font-weight: 600; padding: 2px 10px; border-radius: 20px;">
                                            Queued
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <!-- CTA Button -->
                        <div style="text-align: center; margin: 28px 0;">
                            <a href="{ticket_url}"
                               style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; padding: 13px 32px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600; font-size: 15px; letter-spacing: 0.2px;">
                                Track Your Ticket
                            </a>
                        </div>

                        <p style="margin: 24px 0 0; font-size: 13px; color: #888;">
                            Or copy this link into your browser:<br>
                            <a href="{ticket_url}" style="color: #667eea; word-break: break-all;">{ticket_url}</a>
                        </p>
                    </div>

                    <!-- Footer -->
                    <div style="padding: 20px 40px; border-top: 1px solid #eeeeee; text-align: center;">
                        <p style="margin: 0; color: #aaa; font-size: 12px;">
                            You received this email because you submitted a ticket.<br>
                            &copy; {__import__('datetime').date.today().year} <strong>Shakwa</strong>. All rights reserved.
                        </p>
                    </div>

                </div>
            </body>
        </html>
        """

        return self.send_email(
            to_email=to_email,
            subject=f"Ticket #{short_id} Received – We're on it!",
            html_content=html_content,
        )


# Create a singleton instance
email_service = EmailService()

