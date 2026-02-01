"""
Notification Service for MigrationGuard AI.

This module provides notification capabilities:
- Email notifications
- Webhook notifications for proactive communications
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx

from migrationguard_ai.core.config import get_settings


logger = logging.getLogger(__name__)


class EmailNotificationSender:
    """
    Email notification sender using SMTP.
    
    Supports both plain text and HTML emails.
    """
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        use_tls: bool = True
    ):
        """
        Initialize email sender.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            use_tls: Whether to use TLS
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.use_tls = use_tls
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email notification.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)
            
            # Attach plain text
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                
                recipients = [to_email]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)
                
                server.sendmail(self.from_email, recipients, msg.as_string())
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False
    
    async def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Send email to multiple recipients.
        
        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            
        Returns:
            Dictionary mapping email addresses to success status
        """
        results = {}
        
        for recipient in recipients:
            success = await self.send_email(
                to_email=recipient,
                subject=subject,
                body=body,
                html_body=html_body
            )
            results[recipient] = success
        
        return results


class WebhookNotificationSender:
    """
    Webhook notification sender for proactive communications.
    
    Sends HTTP POST requests to configured webhook endpoints.
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize webhook sender.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None
    ) -> bool:
        """
        Send a webhook notification.
        
        Args:
            url: Webhook URL
            payload: JSON payload to send
            headers: Optional custom headers
            auth_token: Optional authentication token
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            request_headers = headers or {}
            
            # Add authentication if provided
            if auth_token:
                request_headers['Authorization'] = f"Bearer {auth_token}"
            
            # Add default headers
            request_headers.setdefault('Content-Type', 'application/json')
            request_headers.setdefault('User-Agent', 'MigrationGuard-AI/1.0')
            
            # Send webhook
            response = await self.client.post(
                url,
                json=payload,
                headers=request_headers
            )
            
            response.raise_for_status()
            
            logger.info(f"Webhook sent to {url}: {response.status_code}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to send webhook to {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook: {e}", exc_info=True)
            return False
    
    async def send_bulk_webhook(
        self,
        webhooks: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Send webhooks to multiple endpoints.
        
        Args:
            webhooks: List of webhook configurations, each containing:
                - url: Webhook URL
                - payload: JSON payload
                - headers: Optional headers
                - auth_token: Optional auth token
                
        Returns:
            Dictionary mapping URLs to success status
        """
        results = {}
        
        for webhook in webhooks:
            url = webhook['url']
            success = await self.send_webhook(
                url=url,
                payload=webhook.get('payload', {}),
                headers=webhook.get('headers'),
                auth_token=webhook.get('auth_token')
            )
            results[url] = success
        
        return results
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class NotificationService:
    """
    Unified notification service.
    
    Provides a single interface for sending notifications via email and webhooks.
    """
    
    def __init__(self):
        """Initialize notification service from configuration."""
        settings = get_settings()
        
        # Initialize email sender if configured
        self.email_sender = None
        if all(hasattr(settings, attr) for attr in [
            'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'FROM_EMAIL'
        ]):
            self.email_sender = EmailNotificationSender(
                smtp_host=settings.SMTP_HOST,
                smtp_port=settings.SMTP_PORT,
                smtp_user=settings.SMTP_USER,
                smtp_password=settings.SMTP_PASSWORD,
                from_email=settings.FROM_EMAIL,
                use_tls=getattr(settings, 'SMTP_USE_TLS', True)
            )
        
        # Initialize webhook sender
        self.webhook_sender = WebhookNotificationSender()
        
        # Load notification templates
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Load notification templates.
        
        Returns:
            Dictionary of templates by name
        """
        return {
            "issue_detected": {
                "subject": "Issue Detected: {issue_type}",
                "body": """
Hello,

We've detected an issue that may affect your service:

Issue Type: {issue_type}
Severity: {severity}
Merchant ID: {merchant_id}
Description: {description}

Our system is analyzing the issue and will take appropriate action.

Best regards,
MigrationGuard AI
                """.strip(),
                "html": """
<html>
<body>
<h2>Issue Detected: {issue_type}</h2>
<p>We've detected an issue that may affect your service:</p>
<ul>
<li><strong>Issue Type:</strong> {issue_type}</li>
<li><strong>Severity:</strong> {severity}</li>
<li><strong>Merchant ID:</strong> {merchant_id}</li>
<li><strong>Description:</strong> {description}</li>
</ul>
<p>Our system is analyzing the issue and will take appropriate action.</p>
<p>Best regards,<br>MigrationGuard AI</p>
</body>
</html>
                """.strip()
            },
            "issue_resolved": {
                "subject": "Issue Resolved: {issue_type}",
                "body": """
Hello,

Good news! The issue has been resolved:

Issue Type: {issue_type}
Merchant ID: {merchant_id}
Resolution: {resolution}
Resolved At: {resolved_at}

If you have any questions, please contact support.

Best regards,
MigrationGuard AI
                """.strip(),
                "html": """
<html>
<body>
<h2>Issue Resolved: {issue_type}</h2>
<p>Good news! The issue has been resolved:</p>
<ul>
<li><strong>Issue Type:</strong> {issue_type}</li>
<li><strong>Merchant ID:</strong> {merchant_id}</li>
<li><strong>Resolution:</strong> {resolution}</li>
<li><strong>Resolved At:</strong> {resolved_at}</li>
</ul>
<p>If you have any questions, please contact support.</p>
<p>Best regards,<br>MigrationGuard AI</p>
</body>
</html>
                """.strip()
            },
            "action_required": {
                "subject": "Action Required: {action_type}",
                "body": """
Hello,

An action requires your attention:

Action Type: {action_type}
Merchant ID: {merchant_id}
Description: {description}
Required By: {required_by}

Please review and take appropriate action.

Best regards,
MigrationGuard AI
                """.strip(),
                "html": """
<html>
<body>
<h2>Action Required: {action_type}</h2>
<p>An action requires your attention:</p>
<ul>
<li><strong>Action Type:</strong> {action_type}</li>
<li><strong>Merchant ID:</strong> {merchant_id}</li>
<li><strong>Description:</strong> {description}</li>
<li><strong>Required By:</strong> {required_by}</li>
</ul>
<p>Please review and take appropriate action.</p>
<p>Best regards,<br>MigrationGuard AI</p>
</body>
</html>
                """.strip()
            }
        }
    
    async def send_notification(
        self,
        notification_type: str,
        recipient: str,
        template_data: Dict[str, Any],
        channel: str = "email"
    ) -> bool:
        """
        Send a notification using a template.
        
        Args:
            notification_type: Type of notification (template name)
            recipient: Recipient (email address or webhook URL)
            template_data: Data to populate template
            channel: Notification channel ('email' or 'webhook')
            
        Returns:
            True if sent successfully, False otherwise
        """
        template = self.templates.get(notification_type)
        if not template:
            logger.error(f"Unknown notification type: {notification_type}")
            return False
        
        if channel == "email" and self.email_sender:
            subject = template["subject"].format(**template_data)
            body = template["body"].format(**template_data)
            html_body = template["html"].format(**template_data)
            
            return await self.email_sender.send_email(
                to_email=recipient,
                subject=subject,
                body=body,
                html_body=html_body
            )
        
        elif channel == "webhook":
            payload = {
                "notification_type": notification_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": template_data
            }
            
            return await self.webhook_sender.send_webhook(
                url=recipient,
                payload=payload
            )
        
        else:
            logger.error(f"Unsupported channel: {channel}")
            return False
    
    async def send_proactive_communication(
        self,
        merchant_ids: List[str],
        message: str,
        subject: str,
        channel: str = "email"
    ) -> Dict[str, bool]:
        """
        Send proactive communication to multiple merchants.
        
        Args:
            merchant_ids: List of merchant IDs
            message: Message content
            subject: Message subject
            channel: Notification channel
            
        Returns:
            Dictionary mapping merchant IDs to success status
        """
        results = {}
        
        # In a real implementation, we would look up merchant contact info
        # For now, we'll use merchant_id as the recipient
        
        for merchant_id in merchant_ids:
            # Construct recipient based on channel
            if channel == "email":
                recipient = f"{merchant_id}@example.com"  # Placeholder
            else:
                recipient = f"https://webhook.example.com/{merchant_id}"  # Placeholder
            
            template_data = {
                "merchant_id": merchant_id,
                "message": message,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if channel == "email" and self.email_sender:
                success = await self.email_sender.send_email(
                    to_email=recipient,
                    subject=subject,
                    body=message
                )
            elif channel == "webhook":
                payload = {
                    "type": "proactive_communication",
                    "merchant_id": merchant_id,
                    "subject": subject,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
                success = await self.webhook_sender.send_webhook(
                    url=recipient,
                    payload=payload
                )
            else:
                success = False
            
            results[merchant_id] = success
        
        return results
    
    async def close(self):
        """Close all notification clients."""
        await self.webhook_sender.close()


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """
    Get singleton notification service instance.
    
    Returns:
        Notification service instance
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
