import logging
import json
import requests
from django.core.mail import send_mail
from django.conf import settings
from settings.models import MS365Settings

logger = logging.getLogger(__name__)


class EmailService:
    """Enhanced email service that can use MS365 Graph API or Django's email backend"""
    
    def __init__(self):
        self.ms365_settings = MS365Settings.get_settings()
        self._access_token = None
    
    def get_access_token(self):
        """Get Microsoft Graph API access token for email"""
        if self._access_token:
            return self._access_token
            
        try:
            import msal
            
            app = msal.ConfidentialClientApplication(
                client_id=self.ms365_settings.client_id,
                client_credential=self.ms365_settings.client_secret,
                authority=f"https://login.microsoftonline.com/{self.ms365_settings.tenant_id}"
            )
            
            scopes = ['https://graph.microsoft.com/.default']
            result = app.acquire_token_for_client(scopes)
            
            if "access_token" in result:
                self._access_token = result['access_token']
                return self._access_token
            else:
                logger.error(f"Unable to obtain access token for email: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting MS365 access token for email: {str(e)}")
            return None
    
    def send_email_via_ms365(self, to_email, subject, message, from_email=None):
        """Send email using MS365 Graph API"""
        if not self.ms365_settings.client_id or not self.ms365_settings.client_secret:
            return False, "MS365 not configured"
            
        access_token = self.get_access_token()
        if not access_token:
            return False, "Could not get access token"
            
        from_email = from_email or self.ms365_settings.owner_email
        
        # Prepare email body
        email_body = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": message
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            }
        }
        
        # Send the email
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://graph.microsoft.com/v1.0/users/{from_email}/sendMail"
        
        try:
            response = requests.post(url, headers=headers, json=email_body)
            
            if response.status_code == 202:  # Accepted
                logger.info(f"Email sent successfully via MS365 to {to_email}")
                return True, "Email sent successfully"
            else:
                logger.error(f"Failed to send email via MS365: {response.status_code} - {response.text}")
                return False, f"MS365 API error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error sending email via MS365: {str(e)}")
            return False, f"Exception: {str(e)}"
    
    def send_email_via_django(self, to_email, subject, message, from_email=None):
        """Send email using Django's email backend"""
        try:
            from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@awesometechtraining.com')
            send_mail(subject, message, from_email, [to_email], fail_silently=False)
            logger.info(f"Email sent successfully via Django to {to_email}")
            return True, "Email sent successfully"
        except Exception as e:
            logger.error(f"Error sending email via Django: {str(e)}")
            return False, f"Django email error: {str(e)}"
    
    def send_email(self, to_email, subject, message, from_email=None, prefer_ms365=True):
        """
        Send email with fallback mechanism.
        Try MS365 first (if configured and preferred), then fall back to Django's email backend.
        """
        success = False
        error_messages = []
        
        # Try MS365 first if configured and preferred
        if prefer_ms365 and self.ms365_settings.client_id and self.ms365_settings.client_secret:
            logger.info(f"Attempting to send email via MS365 to {to_email}")
            success, message = self.send_email_via_ms365(to_email, subject, message, from_email)
            if success:
                return True, message
            else:
                error_messages.append(f"MS365: {message}")
                logger.warning(f"MS365 email failed, trying Django backend: {message}")
        
        # Fall back to Django email backend
        logger.info(f"Attempting to send email via Django backend to {to_email}")
        success, message = self.send_email_via_django(to_email, subject, message, from_email)
        if success:
            return True, message
        else:
            error_messages.append(f"Django: {message}")
        
        # Both methods failed
        full_error = "; ".join(error_messages)
        logger.error(f"All email methods failed for {to_email}: {full_error}")
        return False, full_error


def send_webhook_error_email(to_email, error_message, webhook_data):
    """
    Enhanced webhook error email function using the new EmailService.
    This replaces the basic send_mail function in utils.py.
    """
    subject = "Kajabi Webhook Processing Error"
    
    # Format webhook data as a pretty-printed JSON string
    webhook_json = json.dumps(webhook_data, indent=2)
    
    message = f"""
An error occurred while processing a Kajabi webhook:

{error_message}

Original webhook data:
{webhook_json}

Please investigate this issue manually.

---
This email was sent via the enhanced email service with MS365 Graph API support.
"""
    
    email_service = EmailService()
    success, result_message = email_service.send_email(
        to_email=to_email,
        subject=subject,
        message=message,
        prefer_ms365=True
    )
    
    if not success:
        logger.error(f"Failed to send webhook error email to {to_email}: {result_message}")
        # Re-raise exception to maintain compatibility with existing error handling
        raise Exception(f"Email delivery failed: {result_message}")
    
    logger.info(f"Webhook error email sent successfully to {to_email}")


def send_notification_email(to_email, subject, message, from_email=None):
    """
    General purpose notification email function using the enhanced EmailService.
    Can be used for other types of notifications beyond webhook errors.
    """
    email_service = EmailService()
    success, result_message = email_service.send_email(
        to_email=to_email,
        subject=subject,
        message=message,
        from_email=from_email,
        prefer_ms365=True
    )
    
    if not success:
        logger.error(f"Failed to send notification email to {to_email}: {result_message}")
        raise Exception(f"Email delivery failed: {result_message}")
    
    logger.info(f"Notification email sent successfully to {to_email}")
    return True