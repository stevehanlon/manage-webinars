import logging
from datetime import datetime, timedelta
import requests
from django.contrib.auth.models import Group
from settings.models import MS365Settings

logger = logging.getLogger(__name__)


class MS365CalendarService:
    """Service for creating Microsoft 365 calendar invites"""
    
    def __init__(self):
        self.settings = MS365Settings.get_settings()
        self._access_token = None
    
    def get_access_token(self):
        """Get Microsoft Graph API access token"""
        if self._access_token:
            return self._access_token
            
        try:
            import msal
            
            app = msal.ConfidentialClientApplication(
                client_id=self.settings.client_id,
                client_credential=self.settings.client_secret,
                authority=f"https://login.microsoftonline.com/{self.settings.tenant_id}"
            )
            
            scopes = ['https://graph.microsoft.com/.default']
            result = app.acquire_token_for_client(scopes)
            
            if "access_token" in result:
                self._access_token = result['access_token']
                return self._access_token
            else:
                logger.error(f"Unable to obtain access token: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting MS365 access token: {str(e)}")
            return None
    
    def create_webinar_meeting(self, webinar_date, was_auto_created=False):
        """Create a calendar invite for a webinar date"""
        if not self.settings.client_id or not self.settings.client_secret:
            logger.info("MS365 not configured, skipping calendar invite creation")
            return None
            
        access_token = self.get_access_token()
        if not access_token:
            return None
            
        # Get users in the calendar group
        calendar_group = Group.objects.filter(name='calendar').first()
        if not calendar_group:
            logger.warning("Calendar group not found, skipping calendar invite creation")
            return None
            
        attendees = []
        for user in calendar_group.user_set.all():
            if user.email:
                attendees.append({
                    "emailAddress": {
                        "address": user.email,
                        "name": user.get_full_name() or user.username
                    },
                    "type": "required"
                })
        
        if not attendees:
            logger.info("No users in calendar group, skipping calendar invite creation")
            return None
            
        # Prepare meeting details
        webinar = webinar_date.webinar
        start_time = webinar_date.date_time
        end_time = start_time + timedelta(hours=1)  # Default to 1 hour duration
        
        # Format times for Graph API
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Create subject
        subject = f"{webinar.name} - {start_time.strftime('%B %d, %Y at %I:%M %p')}"
        if was_auto_created:
            subject = f"[AUTO-CREATED] {subject}"
        
        # Create description
        description = f"""
        <h2>Webinar Details</h2>
        <p><strong>Webinar:</strong> {webinar.name}</p>
        <p><strong>Date/Time:</strong> {start_time.strftime('%B %d, %Y at %I:%M %p %Z')}</p>
        <p><strong>Status:</strong> {'Auto-created from Kajabi webhook' if was_auto_created else 'Manually created'}</p>
        
        <h3>Zoom Meeting Details</h3>
        <p>Zoom meeting will be created when available.</p>
        
        <h3>Attendees</h3>
        <p>View attendees in the <a href="{webinar_date.get_absolute_url()}">webinar management system</a></p>
        """
        
        # Prepare request body
        body = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": description
            },
            "start": {
                "dateTime": start_time_str,
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time_str,
                "timeZone": "UTC"
            },
            "attendees": attendees,
            "isOnlineMeeting": False,
            "reminderMinutesBeforeStart": 15
        }
        
        # Create the event
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://graph.microsoft.com/v1.0/users/{self.settings.owner_email}/calendar/events"
        
        try:
            response = requests.post(url, headers=headers, json=body)
            
            if response.status_code >= 400:
                logger.error(f"Failed to create MS365 meeting: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
            meeting = response.json()
            logger.info(f"Created MS365 calendar invite for {webinar.name} on {start_time}")
            return meeting
            
        except Exception as e:
            logger.error(f"Error creating MS365 calendar invite: {str(e)}")
            return None
    
    def create_bundle_meeting(self, bundle_date, was_auto_created=False):
        """Create a calendar invite for a bundle date"""
        if not self.settings.client_id or not self.settings.client_secret:
            logger.info("MS365 not configured, skipping calendar invite creation")
            return None
            
        access_token = self.get_access_token()
        if not access_token:
            return None
            
        # Get users in the calendar group
        calendar_group = Group.objects.filter(name='calendar').first()
        if not calendar_group:
            logger.warning("Calendar group not found, skipping calendar invite creation")
            return None
            
        attendees = []
        for user in calendar_group.user_set.all():
            if user.email:
                attendees.append({
                    "emailAddress": {
                        "address": user.email,
                        "name": user.get_full_name() or user.username
                    },
                    "type": "required"
                })
        
        if not attendees:
            logger.info("No users in calendar group, skipping calendar invite creation")
            return None
            
        # Prepare meeting details
        bundle = bundle_date.bundle
        date = bundle_date.date
        
        # Use 9 AM as default time for bundle dates
        start_time = datetime.combine(date, datetime.min.time().replace(hour=9))
        end_time = start_time + timedelta(hours=8)  # All day event
        
        # Format times for Graph API
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Create subject
        subject = f"{bundle.name} - {date.strftime('%B %d, %Y')}"
        if was_auto_created:
            subject = f"[AUTO-CREATED] {subject}"
        
        # Create description
        description = f"""
        <h2>Bundle Details</h2>
        <p><strong>Bundle:</strong> {bundle.name}</p>
        <p><strong>Date:</strong> {date.strftime('%B %d, %Y')}</p>
        <p><strong>Status:</strong> {'Auto-created from Kajabi webhook' if was_auto_created else 'Manually created'}</p>
        
        <h3>Included Webinars</h3>
        <p>View webinar dates in the <a href="{bundle_date.get_absolute_url()}">bundle management system</a></p>
        
        <h3>Attendees</h3>
        <p>View attendees in the <a href="{bundle_date.get_absolute_url()}">bundle management system</a></p>
        """
        
        # Prepare request body
        body = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": description
            },
            "start": {
                "dateTime": start_time_str,
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time_str,
                "timeZone": "UTC"
            },
            "attendees": attendees,
            "isOnlineMeeting": False,
            "isAllDay": True,
            "reminderMinutesBeforeStart": 1440  # 24 hours
        }
        
        # Create the event
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://graph.microsoft.com/v1.0/users/{self.settings.owner_email}/calendar/events"
        
        try:
            response = requests.post(url, headers=headers, json=body)
            
            if response.status_code >= 400:
                logger.error(f"Failed to create MS365 meeting: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
            meeting = response.json()
            logger.info(f"Created MS365 calendar invite for {bundle.name} on {date}")
            return meeting
            
        except Exception as e:
            logger.error(f"Error creating MS365 calendar invite: {str(e)}")
            return None
    
    def send_manual_calendar_invite(self, webinar_date):
        """
        Send calendar invite manually and track the result.
        Returns (success, message)
        """
        from django.utils import timezone
        
        try:
            # Use the existing method but with custom subject
            meeting = self.create_webinar_meeting_with_custom_subject(
                webinar_date, 
                subject=f"Webinar: {webinar_date.webinar.name}"
            )
            
            if meeting:
                # Update tracking fields
                webinar_date.calendar_invite_sent_at = timezone.now()
                webinar_date.calendar_invite_success = True
                webinar_date.calendar_invite_error = ''
                webinar_date.save()
                
                return True, f"Calendar invite sent successfully for {webinar_date.webinar.name}"
            else:
                # Update tracking fields for failure
                webinar_date.calendar_invite_sent_at = timezone.now()
                webinar_date.calendar_invite_success = False
                webinar_date.calendar_invite_error = 'Failed to create calendar invite'
                webinar_date.save()
                
                return False, "Failed to create calendar invite"
                
        except Exception as e:
            error_msg = f"Error sending calendar invite: {str(e)}"
            logger.error(error_msg)
            
            # Update tracking fields for error
            webinar_date.calendar_invite_sent_at = timezone.now()
            webinar_date.calendar_invite_success = False
            webinar_date.calendar_invite_error = error_msg
            webinar_date.save()
            
            return False, error_msg
    
    def create_webinar_meeting_with_custom_subject(self, webinar_date, subject):
        """Create a calendar invite for a webinar date with custom subject"""
        if not self.settings.client_id or not self.settings.client_secret:
            logger.info("MS365 not configured, skipping calendar invite creation")
            return None
            
        access_token = self.get_access_token()
        if not access_token:
            return None
            
        # Get users in the calendar group
        calendar_group = Group.objects.filter(name='calendar').first()
        if not calendar_group:
            logger.warning("Calendar group not found, skipping calendar invite creation")
            return None
            
        attendees = []
        for user in calendar_group.user_set.all():
            if user.email:
                attendees.append({
                    "emailAddress": {
                        "address": user.email,
                        "name": user.get_full_name() or user.username
                    },
                    "type": "required"
                })
        
        if not attendees:
            logger.info("No users in calendar group, skipping calendar invite creation")
            return None
            
        # Prepare meeting details
        webinar = webinar_date.webinar
        start_time = webinar_date.date_time
        end_time = start_time + timedelta(hours=1)  # Default to 1 hour duration
        
        # Format times for Graph API
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Create description
        description = f"""
        <h2>Webinar Details</h2>
        <p><strong>Webinar:</strong> {webinar.name}</p>
        <p><strong>Date/Time:</strong> {start_time.strftime('%B %d, %Y at %I:%M %p %Z')}</p>
        <p><strong>Status:</strong> Manually sent calendar invite</p>
        
        <h3>Zoom Meeting Details</h3>
        <p>Zoom meeting will be created when available.</p>
        
        <h3>Attendees</h3>
        <p>View attendees in the <a href="{webinar_date.get_absolute_url()}">webinar management system</a></p>
        """
        
        # Prepare request body
        body = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": description
            },
            "start": {
                "dateTime": start_time_str,
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time_str,
                "timeZone": "UTC"
            },
            "attendees": attendees,
            "isOnlineMeeting": False,
            "reminderMinutesBeforeStart": 15
        }
        
        # Create the event
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://graph.microsoft.com/v1.0/users/{self.settings.owner_email}/calendar/events"
        
        try:
            response = requests.post(url, headers=headers, json=body)
            
            if response.status_code >= 400:
                logger.error(f"Failed to create MS365 meeting: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
            meeting = response.json()
            logger.info(f"Created manual MS365 calendar invite for {webinar.name} on {start_time}")
            return meeting
            
        except Exception as e:
            logger.error(f"Error creating manual MS365 calendar invite: {str(e)}")
            return None
    
    def send_clinic_calendar_invite(self, clinic_booking):
        """
        Send calendar invite for a clinic booking.
        Returns (success, message)
        """
        from django.utils import timezone
        from django.contrib.auth.models import Group
        
        try:
            if not self.settings.client_id or not self.settings.client_secret:
                return False, "MS365 not configured"
                
            access_token = self.get_access_token()
            if not access_token:
                return False, "Failed to get MS365 access token"
                
            # Get users in the calendar group
            calendar_group = Group.objects.filter(name='calendar').first()
            if not calendar_group:
                return False, "Calendar group not found"
                
            attendees = []
            
            # Add the clinic customer as an attendee
            attendees.append({
                "emailAddress": {
                    "address": clinic_booking.email,
                    "name": clinic_booking.full_name
                },
                "type": "required"
            })
            
            # Add calendar group members
            for user in calendar_group.user_set.all():
                if user.email:
                    attendees.append({
                        "emailAddress": {
                            "address": user.email,
                            "name": user.get_full_name() or user.username
                        },
                        "type": "required"
                    })
            
            if len(attendees) <= 1:  # Only customer, no staff
                return False, "No staff members in calendar group to invite"
                
            # Prepare meeting details
            start_time = clinic_booking.clinic_date
            end_time = start_time + timedelta(minutes=30)  # 30 minute clinic sessions
            
            # Format times for Graph API
            start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
            end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")
            
            # Create subject
            subject = clinic_booking.zoom_meeting_subject
            
            # Create description with all clinic details
            description = f"""
            <h2>Clinic Session Details</h2>
            <p><strong>Customer:</strong> {clinic_booking.full_name}</p>
            <p><strong>Email:</strong> {clinic_booking.email}</p>
            <p><strong>Organization:</strong> {clinic_booking.organization or 'Not provided'}</p>
            <p><strong>Website:</strong> {clinic_booking.website or 'Not provided'}</p>
            <p><strong>Date Submitted:</strong> {clinic_booking.created_at.strftime('%B %d, %Y at %I:%M %p %Z')}</p>
            <p><strong>Clinic Date/Time:</strong> {start_time.strftime('%B %d, %Y at %I:%M %p %Z')}</p>
            
            <h3>Customer Question</h3>
            <p>{clinic_booking.question}</p>
            
            <h3>Zoom Meeting Details</h3>
            """
            
            if clinic_booking.zoom_meeting_id and clinic_booking.zoom_join_url:
                description += f"""
                <p><strong>Meeting ID:</strong> {clinic_booking.zoom_meeting_id}</p>
                <p><strong>Join URL:</strong> <a href="{clinic_booking.zoom_join_url}">{clinic_booking.zoom_join_url}</a></p>
                """
            else:
                description += "<p>Zoom meeting details will be added when available.</p>"
            
            description += f"""
            
            <h3>Management</h3>
            <p><a href="{clinic_booking.get_absolute_url()}">View clinic booking details</a></p>
            """
            
            # Prepare request body
            body = {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": description
                },
                "start": {
                    "dateTime": start_time_str,
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_time_str,
                    "timeZone": "UTC"
                },
                "attendees": attendees,
                "isOnlineMeeting": False,
                "reminderMinutesBeforeStart": 15,
                "showAs": "busy"
            }
            
            # Create the event
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"https://graph.microsoft.com/v1.0/users/{self.settings.owner_email}/calendar/events"
            
            response = requests.post(url, headers=headers, json=body)
            
            if response.status_code >= 400:
                error_msg = f"Failed to create clinic calendar invite: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
            meeting = response.json()
            logger.info(f"Created clinic calendar invite for {clinic_booking.full_name} on {start_time}")
            return True, f"Calendar invite sent successfully for clinic with {clinic_booking.full_name}"
            
        except Exception as e:
            error_msg = f"Error sending clinic calendar invite: {str(e)}"
            logger.error(error_msg)
            return False, error_msg