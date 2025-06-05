import re
import logging
from datetime import datetime, timedelta
from dateutil.parser import parse
from django.utils import timezone
import json

logger = logging.getLogger(__name__)

def parse_webinar_date(date_str):
    """
    Parse a date string from Kajabi webinar form or checkout.
    Returns a datetime object, 'on_demand' string, or None if parsing fails.
    
    Examples:
    - "21 August, 10-11:00 BST"
    - "19 June, 10-11:00 BST"
    - "on demand" (case insensitive)
    """
    try:
        # Check if this is an "on demand" date (case insensitive)
        if 'on demand' in date_str.lower():
            return 'on_demand'
        
        # Extract date and time parts
        # Match patterns like "21 August, 10-11:00 BST" or "19 June, 10-11:00 BST"
        match = re.match(r'(\d+)\s+([A-Za-z]+),\s+(\d+)(?:-\d+)?:(\d+)', date_str)
        if not match:
            return None
        
        day, month, hour, minute = match.groups()
        
        # Create a date string in a format dateutil can parse
        date_time_str = f"{day} {month} {datetime.now().year} {hour}:{minute}"
        parsed_date = parse(date_time_str)
        
        # Convert to timezone-aware datetime first
        parsed_date = timezone.make_aware(parsed_date)
        
        # If parsed date is in the past, assume it's for next year
        current_date = timezone.now()
        if parsed_date < current_date:
            parsed_date = parsed_date.replace(year=current_date.year + 1)
        
        return parsed_date
    
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {str(e)}")
        return None


def find_webinar_by_form_title(form_title):
    """
    Find a webinar that matches a form title.
    Checks main name and aliases for exact and partial matches.
    """
    from .models import Webinar
    
    webinars = Webinar.objects.filter(deleted_at=None)
    
    # First try exact match against all names (main name + aliases)
    for webinar in webinars:
        for name in webinar.get_all_names():
            if name.lower() == form_title.lower():
                return webinar
    
    # Then try partial match against all names
    for webinar in webinars:
        for name in webinar.get_all_names():
            if name.lower() in form_title.lower() or form_title.lower() in name.lower():
                return webinar
    
    return None


def find_bundle_by_form_title(form_title):
    """
    Find a bundle that matches a form title.
    Checks main name and aliases for exact and partial matches.
    """
    from .models import WebinarBundle
    
    bundles = WebinarBundle.objects.filter(deleted_at=None)
    
    # First try exact match against all names (main name + aliases)
    for bundle in bundles:
        for name in bundle.get_all_names():
            if name.lower() == form_title.lower():
                return bundle
    
    # Then try partial match against all names
    for bundle in bundles:
        for name in bundle.get_all_names():
            if name.lower() in form_title.lower() or form_title.lower() in name.lower():
                return bundle
    
    return None


def find_webinar_date(webinar, date_time):
    """
    Find a webinar date close to the given date and time.
    Uses fuzzy matching with a 1-hour window.
    Returns the found date or None if not found.
    """
    if not date_time:
        return None
    
    date_time_min = date_time - timedelta(hours=1)
    date_time_max = date_time + timedelta(hours=1)
    
    # Find dates that are within 1 hour of the parsed date
    dates = webinar.active_dates().filter(
        date_time__gte=date_time_min,
        date_time__lte=date_time_max
    )
    
    if dates.exists():
        return dates.first()
    
    return None


def create_on_demand_attendee(webinar, first_name, last_name, email, organization=''):
    """
    Create or update an on-demand attendee for a webinar.
    Returns the attendee and whether it was created.
    """
    from .models import OnDemandAttendee
    
    attendee, created = OnDemandAttendee.objects.get_or_create(
        webinar=webinar,
        email=email,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'organization': organization
        }
    )
    
    # If attendee existed but was deleted, restore it
    if not created and attendee.is_deleted:
        attendee.deleted_at = None
        attendee.first_name = first_name
        attendee.last_name = last_name
        attendee.organization = organization
        attendee.save()
    
    logger.info(f"{'Created' if created else 'Updated'} on-demand attendee {email} for {webinar.name}")
    return attendee, created


def find_bundle_date(bundle, date_time):
    """
    Find a bundle date that matches the given date.
    Returns the found date or None if not found.
    """
    if not date_time:
        return None
    
    # Extract just the date part
    target_date = date_time.date()
    
    # Find bundle dates that match the date
    dates = bundle.active_dates().filter(
        date=target_date
    )
    
    if dates.exists():
        return dates.first()
    
    return None


def send_unrecognized_date_error_email(error_email, webinar_or_bundle_name, date_str, parsed_date, webhook_data, is_bundle=False):
    """Send an error email when a booking is made for an unrecognized date."""
    from .email_service import send_notification_email
    
    entity_type = "bundle" if is_bundle else "webinar"
    
    subject = f"Booking for Unrecognized {entity_type.title()} Date - {webinar_or_bundle_name}"
    
    message = f"""
BOOKING FOR UNRECOGNIZED DATE RECEIVED

A booking has been received for a {entity_type} date that does not exist in the system.

{entity_type.title()} Details:
- Name: {webinar_or_bundle_name}
- Requested Date: {date_str}
- Parsed Date: {parsed_date.strftime('%Y-%m-%d %H:%M:%S %Z') if parsed_date else 'Could not parse'}

Attendee Information:
- Name: {webhook_data.get('first_name', 'N/A')} {webhook_data.get('last_name', 'N/A')}
- Email: {webhook_data.get('email', 'N/A')}

ACTION REQUIRED:
1. Create the missing {entity_type} date in the system
2. Manually register this attendee for the correct date

Raw Webhook Data:
{json.dumps(webhook_data, indent=2)}

This booking was rejected because auto-creation of dates has been disabled.
Please create the date manually and register the attendee.

---
Kajabi Webinar Manager
    """
    
    try:
        send_notification_email(
            to_email=error_email,
            subject=subject,
            message=message
        )
        logger.info(f"Sent unrecognized date error email to {error_email} for {entity_type} {webinar_or_bundle_name}")
    except Exception as e:
        logger.error(f"Failed to send unrecognized date error email: {str(e)}")


def process_kajabi_webhook(data, request):
    """
    Process Kajabi webhook data and register attendee.
    Returns (success, message, attendee_id)
    """
    from .models import Webinar, WebinarDate, Attendee, WebinarBundle, BundleDate, BundleAttendee
    
    try:
        # Determine which type of webhook is being received
        event_type = data.get('event', '')
        
        if event_type == 'form_submission.created':
            # Process form submission
            payload = data.get('payload', {})
            form_title = payload.get('form_title', '')
            
            # First check if it's a bundle
            bundle = find_bundle_by_form_title(form_title)
            if bundle:
                # Process as bundle
                return process_bundle_webhook(bundle, payload, 'form', data)
            
            # Find the matching webinar
            webinar = find_webinar_by_form_title(form_title)
            if not webinar:
                return False, f"No matching webinar or bundle found for form: {form_title}", None
            
            # Extract attendee information
            first_name = payload.get('First Name', '')
            last_name = payload.get('Surname', '')  # Form submissions have Surname field
            email = payload.get('Email', '')
            organization = payload.get('Organisation', '')  # Extract organization from form
            
            # Extract date from payload using the form_date_field from the webinar
            date_str = payload.get(webinar.form_date_field, '')
            
            # Debug logging
            logger.info(f"Form submission extraction - Webinar: {webinar.name}, form_date_field: '{webinar.form_date_field}'")
            logger.info(f"Extracted - first_name: '{first_name}', email: '{email}', date_str: '{date_str}'")
            
        elif event_type == 'purchase.created':
            # Process purchase event
            payload = data.get('payload', {})
            offer_title = payload.get('offer_title', '')
            
            # First check if it's a bundle
            bundle = find_bundle_by_form_title(offer_title)
            if bundle:
                # Process as bundle
                return process_bundle_webhook(bundle, payload, 'purchase', data)
            
            # Find the matching webinar
            webinar = find_webinar_by_form_title(offer_title)
            if not webinar:
                return False, f"No matching webinar or bundle found for offer: {offer_title}", None
            
            # Extract attendee information
            first_name = payload.get('member_first_name', '')
            last_name = payload.get('member_last_name', '')
            email = payload.get('member_email', '')
            organization = ''  # Purchase events don't typically have organization data
            
            # Extract date from payload using the checkout_date_field from the webinar
            date_str = payload.get(webinar.checkout_date_field, '')
            
        else:
            return False, f"Unsupported event type: {event_type}", None
        
        # Validate required fields
        if not all([first_name, email, date_str]):
            return False, "Missing required fields: first_name, email, or date", None
        
        # Parse date string to datetime or 'on_demand'
        parsed_date = parse_webinar_date(date_str)
        if not parsed_date:
            return False, f"Could not parse date: {date_str}", None
        
        # Handle on-demand webinars
        if parsed_date == 'on_demand':
            attendee, created = create_on_demand_attendee(webinar, first_name, last_name, email, organization)
            
            # For on-demand attendees, activate immediately
            if not attendee.activation_sent_at:
                try:
                    from .activation_service import activate_attendee
                    success, activation_message = activate_attendee(attendee)
                    if success:
                        logger.info(f"Immediately activated on-demand attendee {email}: {activation_message}")
                    else:
                        logger.warning(f"Failed to activate on-demand attendee {email}: {activation_message}")
                except Exception as e:
                    logger.error(f"Error activating on-demand attendee {email}: {str(e)}")
            
            status = "Created" if created else "Updated"
            activation_status = ""
            if attendee.activation_sent_at and attendee.activation_success:
                activation_status = " (activated immediately)"
            elif attendee.activation_sent_at and not attendee.activation_success:
                activation_status = " (activation failed)"
            
            return True, f"{status} on-demand attendee for {webinar.name}{activation_status}", attendee.id
        else:
            # Find matching webinar date (no auto-creation for regular dates)
            webinar_date = find_webinar_date(webinar, parsed_date)
            if not webinar_date:
                # Send error email for unrecognized date
                attendee_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'event_type': event_type,
                    'date_str': date_str,
                    'parsed_date': parsed_date.isoformat() if parsed_date else None
                }
                send_unrecognized_date_error_email(
                    error_email=webinar.error_notification_email,
                    webinar_or_bundle_name=webinar.name,
                    date_str=date_str,
                    parsed_date=parsed_date,
                    webhook_data=attendee_data,
                    is_bundle=False
                )
                return False, f"No webinar date found for {date_str}. Error email sent to {webinar.error_notification_email}.", None
        
            # Create or update regular attendee for scheduled dates
            attendee, created = Attendee.objects.get_or_create(
                webinar_date=webinar_date,
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'organization': organization
                }
            )
            
            # If attendee existed but was deleted, restore it
            if not created and attendee.is_deleted:
                attendee.deleted_at = None
                attendee.first_name = first_name
                attendee.last_name = last_name
                attendee.organization = organization
                attendee.save()
            
            # Try to register attendee in Zoom if webinar has Zoom meeting ID
            if webinar_date.zoom_meeting_id and not attendee.zoom_registrant_id:
                try:
                    from .zoom_service import ZoomService
                    zoom_service = ZoomService()
                    
                    result = zoom_service.register_attendee(
                        webinar_date.zoom_meeting_id,
                        first_name,
                        last_name,
                        email
                    )
                    
                    if result['success']:
                        attendee.zoom_registrant_id = result['registrant_id']
                        attendee.zoom_join_url = result['join_url']
                        attendee.zoom_invite_link = result.get('invite_link', result['join_url'])
                        attendee.zoom_registered_at = timezone.now()
                        attendee.zoom_registration_error = ''
                        logger.info(f"Registered attendee {email} in Zoom webinar {webinar_date.zoom_meeting_id}")
                    else:
                        attendee.zoom_registration_error = result['error']
                        logger.warning(f"Failed to register attendee {email} in Zoom: {result['error']}")
                    
                    attendee.save()
                    
                except Exception as e:
                    error_msg = f"Error registering attendee in Zoom: {str(e)}"
                    attendee.zoom_registration_error = error_msg
                    attendee.save()
                    logger.error(error_msg)
        
            status = "Created" if created else "Updated"
            zoom_status = ""
            
            if webinar_date.zoom_meeting_id:
                if attendee.zoom_registrant_id:
                    zoom_status = " and registered in Zoom"
                elif attendee.zoom_registration_error:
                    zoom_status = " (Zoom registration failed)"
            
            return True, f"{status} attendee for {webinar.name} on {webinar_date.date_time}{zoom_status}", attendee.id
    
    except Exception as e:
        error_message = f"Error processing webhook: {str(e)}"
        logger.error(error_message)
        
        # Send error notification email with details
        try:
            error_email = webinar.error_notification_email if 'webinar' in locals() and webinar else "info@awesometechtraining.com"
            send_webhook_error_email(error_email, error_message, data)
        except Exception as email_error:
            logger.error(f"Failed to send error email: {str(email_error)}")
        
        return False, error_message, None


def process_bundle_webhook(bundle, payload, webhook_type, data):
    """
    Process webhook for bundle purchases.
    """
    from .models import BundleAttendee
    
    try:
        # Extract attendee information based on webhook type
        if webhook_type == 'form':
            first_name = payload.get('First Name', '')
            last_name = payload.get('Surname', '')
            email = payload.get('Email', '')
            organization = payload.get('Organisation', '')
            date_str = payload.get(bundle.form_date_field, '')
        else:  # purchase
            first_name = payload.get('member_first_name', '')
            last_name = payload.get('member_last_name', '')
            email = payload.get('member_email', '')
            organization = ''
            date_str = payload.get(bundle.checkout_date_field, '')
        
        # Validate required fields
        if not all([first_name, email, date_str]):
            return False, "Missing required fields: first_name, email, or date", None
        
        # Parse date string to datetime
        parsed_date = parse_webinar_date(date_str)
        if not parsed_date:
            return False, f"Could not parse date: {date_str}", None
        
        # Find matching bundle date (no auto-creation)
        bundle_date = find_bundle_date(bundle, parsed_date)
        if not bundle_date:
            # Send error email for unrecognized date
            attendee_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'webhook_type': webhook_type,
                'date_str': date_str,
                'parsed_date': parsed_date.isoformat() if parsed_date else None
            }
            send_unrecognized_date_error_email(
                error_email=bundle.error_notification_email,
                webinar_or_bundle_name=bundle.name,
                date_str=date_str,
                parsed_date=parsed_date,
                webhook_data=attendee_data,
                is_bundle=True
            )
            return False, f"No bundle date found for {date_str}. Error email sent to {bundle.error_notification_email}.", None
        
        # Create or update bundle attendee
        attendee, created = BundleAttendee.objects.get_or_create(
            bundle_date=bundle_date,
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'organization': organization
            }
        )
        
        # If attendee existed but was deleted, restore it
        if not created and attendee.is_deleted:
            attendee.deleted_at = None
            attendee.first_name = first_name
            attendee.last_name = last_name
            attendee.organization = organization
            attendee.save()
        
        status = "Created" if created else "Updated"
        return True, f"{status} bundle attendee for {bundle.name} on {bundle_date.date}", attendee.id
        
    except Exception as e:
        error_message = f"Error processing bundle webhook: {str(e)}"
        logger.error(error_message)
        
        # Send error notification email with details
        try:
            error_email = bundle.error_notification_email
            send_webhook_error_email(error_email, error_message, data)
        except Exception as email_error:
            logger.error(f"Failed to send error email: {str(email_error)}")
        
        return False, error_message, None


def send_webhook_error_email(to_email, error_message, webhook_data):
    """Send an email notification about webhook processing errors using enhanced email service."""
    # Import the enhanced email function
    from .email_service import send_webhook_error_email as enhanced_send_webhook_error_email
    
    # Use the enhanced email service
    enhanced_send_webhook_error_email(to_email, error_message, webhook_data)