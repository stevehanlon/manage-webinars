import requests
import logging
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class KajabiActivationService:
    """Service for triggering Kajabi grant offer activations."""
    
    def __init__(self):
        self.timeout = 30  # 30 second timeout for HTTP requests
    
    def activate_attendee(self, attendee):
        """
        Activate grant offer for a single attendee.
        Returns (success, message)
        """
        if hasattr(attendee, 'webinar_date'):
            # Regular webinar attendee
            activation_url = attendee.webinar_date.webinar.kajabi_grant_activation_hook_url
            attendee_type = "webinar"
        else:
            # Bundle attendee
            activation_url = attendee.bundle_date.bundle.kajabi_grant_activation_hook_url
            attendee_type = "bundle"
        
        try:
            # Prepare payload for Kajabi webhook
            payload = {
                'email': attendee.email,
                'first_name': attendee.first_name,
                'last_name': attendee.last_name,
                'activation_type': attendee_type,
                'timestamp': timezone.now().isoformat()
            }
            
            # Make HTTP POST request to Kajabi webhook
            response = requests.post(
                activation_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Kajabi-Webinar-Manager/1.0'
                },
                timeout=self.timeout
            )
            
            # Check if request was successful
            if response.status_code in [200, 201, 202]:
                # Update attendee activation status
                attendee.activation_sent_at = timezone.now()
                attendee.activation_success = True
                attendee.activation_error = ''
                attendee.save()
                
                logger.info(f"Successfully activated grant for {attendee.email}")
                return True, f"Grant activation sent successfully for {attendee.email}"
            
            else:
                # Handle HTTP error
                error_msg = f"HTTP {response.status_code}: {response.text}"
                attendee.activation_sent_at = timezone.now()
                attendee.activation_success = False
                attendee.activation_error = error_msg
                attendee.save()
                
                logger.error(f"Failed to activate grant for {attendee.email}: {error_msg}")
                return False, f"Activation failed for {attendee.email}: {error_msg}"
        
        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            attendee.activation_sent_at = timezone.now()
            attendee.activation_success = False
            attendee.activation_error = error_msg
            attendee.save()
            
            logger.error(f"Timeout activating grant for {attendee.email}")
            return False, f"Activation timeout for {attendee.email}"
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            attendee.activation_sent_at = timezone.now()
            attendee.activation_success = False
            attendee.activation_error = error_msg
            attendee.save()
            
            logger.error(f"Request error activating grant for {attendee.email}: {str(e)}")
            return False, f"Activation error for {attendee.email}: {str(e)}"
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            attendee.activation_sent_at = timezone.now()
            attendee.activation_success = False
            attendee.activation_error = error_msg
            attendee.save()
            
            logger.error(f"Unexpected error activating grant for {attendee.email}: {str(e)}")
            return False, f"Unexpected error for {attendee.email}: {str(e)}"
    
    def activate_webinar_date_attendees(self, webinar_date):
        """
        Activate grant offers for all attendees of a webinar date.
        Returns (success_count, failure_count, messages)
        """
        all_attendees = webinar_date.get_all_attendees()
        success_count = 0
        failure_count = 0
        messages = []
        
        for attendee in all_attendees:
            # Skip if already activated
            if attendee.activation_sent_at:
                messages.append(f"Skipped {attendee.email} (already activated)")
                continue
            
            success, message = self.activate_attendee(attendee)
            if success:
                success_count += 1
            else:
                failure_count += 1
            messages.append(message)
        
        return success_count, failure_count, messages
    
    def activate_pending_attendees(self):
        """
        Activate grant offers for all attendees who need activation
        (webinar ended 2+ hours ago and not yet activated).
        Returns (success_count, failure_count, messages)
        """
        from .models import Attendee, BundleAttendee
        
        success_count = 0
        failure_count = 0
        messages = []
        
        # Find regular attendees who need activation
        attendees = Attendee.objects.filter(
            deleted_at=None,
            activation_sent_at=None
        ).select_related('webinar_date', 'webinar_date__webinar')
        
        for attendee in attendees:
            if attendee.needs_activation:
                success, message = self.activate_attendee(attendee)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                messages.append(message)
        
        # Find bundle attendees who need activation
        bundle_attendees = BundleAttendee.objects.filter(
            deleted_at=None,
            activation_sent_at=None
        ).select_related('bundle_date', 'bundle_date__bundle')
        
        for attendee in bundle_attendees:
            if attendee.needs_activation:
                success, message = self.activate_attendee(attendee)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                messages.append(message)
        
        return success_count, failure_count, messages


def activate_attendee(attendee):
    """Convenience function to activate a single attendee."""
    service = KajabiActivationService()
    return service.activate_attendee(attendee)


def activate_webinar_date_attendees(webinar_date):
    """Convenience function to activate all attendees for a webinar date."""
    service = KajabiActivationService()
    return service.activate_webinar_date_attendees(webinar_date)


def activate_pending_attendees():
    """Convenience function to activate all pending attendees."""
    service = KajabiActivationService()
    return service.activate_pending_attendees()