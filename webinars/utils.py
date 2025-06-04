import re
import logging
from datetime import datetime, timedelta
from dateutil.parser import parse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import json

logger = logging.getLogger(__name__)

def parse_webinar_date(date_str):
    """
    Parse a date string from Kajabi webinar form or checkout.
    Returns a datetime object or None if parsing fails.
    
    Examples:
    - "21 August, 10-11:00 BST"
    - "19 June, 10-11:00 BST"
    """
    try:
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


def find_or_create_webinar_date(webinar, date_time, auto_create=True):
    """
    Find a webinar date close to the given date and time.
    Uses fuzzy matching with a 1-hour window.
    If not found and auto_create is True, creates a new webinar date.
    """
    if not date_time:
        return None, False
    
    date_time_min = date_time - timedelta(hours=1)
    date_time_max = date_time + timedelta(hours=1)
    
    # Find dates that are within 1 hour of the parsed date
    dates = webinar.active_dates().filter(
        date_time__gte=date_time_min,
        date_time__lte=date_time_max
    )
    
    if dates.exists():
        return dates.first(), False
    
    # If no date found and auto_create is enabled, create a new one
    if auto_create:
        from .models import WebinarDate
        logger.info(f"Auto-creating webinar date for {webinar.name} at {date_time}")
        new_date = WebinarDate.objects.create(
            webinar=webinar,
            date_time=date_time
        )
        
        # Send calendar invite for auto-created date
        try:
            from .ms365_service import MS365CalendarService
            ms365_service = MS365CalendarService()
            ms365_service.create_webinar_meeting(new_date, was_auto_created=True)
        except Exception as e:
            logger.error(f"Failed to create calendar invite: {str(e)}")
        
        return new_date, True
    
    return None, False


def find_or_create_bundle_date(bundle, date_time, auto_create=True):
    """
    Find a bundle date that matches the given date.
    If not found and auto_create is True, creates a new bundle date.
    """
    if not date_time:
        return None, False
    
    # Extract just the date part
    target_date = date_time.date()
    
    # Find bundle dates that match the date
    dates = bundle.active_dates().filter(
        date=target_date
    )
    
    if dates.exists():
        return dates.first(), False
    
    # If no date found and auto_create is enabled, create a new one
    if auto_create:
        from .models import BundleDate
        logger.info(f"Auto-creating bundle date for {bundle.name} on {target_date}")
        new_date = BundleDate.objects.create(
            bundle=bundle,
            date=target_date
        )
        
        # Send calendar invite for auto-created date
        try:
            from .ms365_service import MS365CalendarService
            ms365_service = MS365CalendarService()
            ms365_service.create_bundle_meeting(new_date, was_auto_created=True)
        except Exception as e:
            logger.error(f"Failed to create calendar invite: {str(e)}")
        
        return new_date, True
    
    return None, False


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
            last_name = '' # Form submissions may not have last name
            email = payload.get('Email', '')
            
            # Extract date from payload using the form_date_field from the webinar
            date_str = payload.get(webinar.form_date_field, '')
            
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
            
            # Extract date from payload using the checkout_date_field from the webinar
            date_str = payload.get(webinar.checkout_date_field, '')
            
        else:
            return False, f"Unsupported event type: {event_type}", None
        
        # Validate required fields
        if not all([first_name, email, date_str]):
            return False, "Missing required fields: first_name, email, or date", None
        
        # Parse date string to datetime
        parsed_date = parse_webinar_date(date_str)
        if not parsed_date:
            return False, f"Could not parse date: {date_str}", None
        
        # Find or create matching webinar date
        webinar_date, was_created = find_or_create_webinar_date(webinar, parsed_date)
        if not webinar_date:
            return False, f"Could not find or create webinar date for: {parsed_date}", None
        
        # Create or update attendee
        attendee, created = Attendee.objects.get_or_create(
            webinar_date=webinar_date,
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name
            }
        )
        
        # If attendee existed but was deleted, restore it
        if not created and attendee.is_deleted:
            attendee.deleted_at = None
            attendee.first_name = first_name
            attendee.last_name = last_name
            attendee.save()
        
        status = "Created" if created else "Updated"
        date_status = " (date auto-created)" if was_created else ""
        return True, f"{status} attendee for {webinar.name} on {webinar_date.date_time}{date_status}", attendee.id
    
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
            last_name = ''
            email = payload.get('Email', '')
            date_str = payload.get(bundle.form_date_field, '')
        else:  # purchase
            first_name = payload.get('member_first_name', '')
            last_name = payload.get('member_last_name', '')
            email = payload.get('member_email', '')
            date_str = payload.get(bundle.checkout_date_field, '')
        
        # Validate required fields
        if not all([first_name, email, date_str]):
            return False, "Missing required fields: first_name, email, or date", None
        
        # Parse date string to datetime
        parsed_date = parse_webinar_date(date_str)
        if not parsed_date:
            return False, f"Could not parse date: {date_str}", None
        
        # Find or create matching bundle date
        bundle_date, was_created = find_or_create_bundle_date(bundle, parsed_date)
        if not bundle_date:
            return False, f"Could not find or create bundle date for: {parsed_date}", None
        
        # Create or update bundle attendee
        attendee, created = BundleAttendee.objects.get_or_create(
            bundle_date=bundle_date,
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name
            }
        )
        
        # If attendee existed but was deleted, restore it
        if not created and attendee.is_deleted:
            attendee.deleted_at = None
            attendee.first_name = first_name
            attendee.last_name = last_name
            attendee.save()
        
        status = "Created" if created else "Updated"
        date_status = " (date auto-created)" if was_created else ""
        return True, f"{status} bundle attendee for {bundle.name} on {bundle_date.date}{date_status}", attendee.id
        
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
    """Send an email notification about webhook processing errors."""
    subject = "Kajabi Webhook Processing Error"
    
    # Format webhook data as a pretty-printed JSON string
    webhook_json = json.dumps(webhook_data, indent=2)
    
    message = f"""
An error occurred while processing a Kajabi webhook:

{error_message}

Original webhook data:
{webhook_json}

Please investigate this issue manually.
"""
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [to_email]
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)