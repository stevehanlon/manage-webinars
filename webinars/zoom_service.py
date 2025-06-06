import requests
import jwt
import time
from datetime import datetime, timedelta
from django.conf import settings as django_settings
from settings.models import ZoomSettings


class ZoomAPIError(Exception):
    """Custom exception for Zoom API errors."""
    pass


class ZoomService:
    """Service for interacting with Zoom API to create meetings/webinars."""
    
    BASE_URL = "https://api.zoom.us/v2"
    
    def __init__(self):
        self.zoom_settings = ZoomSettings.get_settings()
        if not self._is_configured():
            raise ZoomAPIError("Zoom is not properly configured. Please check settings.")
    
    def _is_configured(self):
        """Check if all required Zoom settings are configured."""
        return bool(
            self.zoom_settings.client_id and 
            self.zoom_settings.client_secret and 
            self.zoom_settings.account_id
        )
    
    def _generate_jwt_token(self):
        """Generate JWT token for Server-to-Server OAuth."""
        payload = {
            'iss': self.zoom_settings.client_id,
            'exp': int(time.time()) + 3600,  # Token expires in 1 hour
            'iat': int(time.time()),
            'aud': 'zoom',
            'alg': 'HS256'
        }
        
        token = jwt.encode(payload, self.zoom_settings.client_secret, algorithm='HS256')
        return token
    
    def _get_access_token(self):
        """Get access token using Server-to-Server OAuth."""
        try:
            url = "https://zoom.us/oauth/token"
            data = {
                'grant_type': 'account_credentials',
                'account_id': self.zoom_settings.account_id
            }
            
            auth = (self.zoom_settings.client_id, self.zoom_settings.client_secret)
            
            response = requests.post(url, data=data, auth=auth)
            response.raise_for_status()
            
            return response.json()['access_token']
        except requests.RequestException as e:
            raise ZoomAPIError(f"Failed to get access token: {str(e)}")
    
    def _make_api_request(self, method, endpoint, data=None):
        """Make authenticated API request to Zoom."""
        access_token = self._get_access_token()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            else:
                raise ZoomAPIError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            error_msg = f"Zoom API request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_msg += f" - {error_details.get('message', 'Unknown error')}"
                except:
                    error_msg += f" - HTTP {e.response.status_code}"
            raise ZoomAPIError(error_msg)
    
    def create_webinar(self, webinar_date):
        """
        Create a Zoom webinar for a webinar date.
        
        Args:
            webinar_date: WebinarDate instance
            
        Returns:
            dict: Zoom webinar data including webinar_id, join_url, etc.
        """
        # Prepare webinar data
        webinar_data = {
            "topic": webinar_date.webinar.name,
            "type": 5,  # Scheduled webinar
            "start_time": webinar_date.date_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration": 60,  # Default duration in minutes
            "timezone": "Europe/London",  # Automatically handles BST/GMT transitions
            "settings": {
                "host_video": True,
                "panelists_video": False,
                "practice_session": False,
                "hd_video": False,
                "approval_type": 0,  # Automatically approve
                "audio": "both",
                "auto_recording": "none",
                "enforce_login": False,
                "registrants_email_notification": True,
                "close_registration": False,
                "show_share_button": True,
                "allow_multiple_devices": True,
                "on_demand": False,
                "global_dial_in_countries": ["US"],
                "contact_name": "Webinar Host",
                "contact_email": "host@example.com"
            }
        }
        
        # Add template if configured
        if self.zoom_settings.webinar_template_id:
            webinar_data["template_id"] = self.zoom_settings.webinar_template_id
        
        # Use 'me' to get the current authenticated user
        user_response = self._make_api_request('GET', '/users/me')
        user_id = user_response['id']
        
        # Create the webinar
        endpoint = f"/users/{user_id}/webinars"
        webinar_response = self._make_api_request('POST', endpoint, webinar_data)
        
        return {
            'webinar_id': str(webinar_response['id']),
            'join_url': webinar_response['join_url'],
            'start_url': webinar_response['start_url'],
            'registration_url': webinar_response.get('registration_url', ''),
            'password': webinar_response.get('password', ''),
            'zoom_response': webinar_response
        }
    
    def register_attendee(self, webinar_id, first_name, last_name, email):
        """
        Register an attendee for a Zoom webinar.
        
        Args:
            webinar_id: Zoom webinar ID
            first_name: Attendee's first name
            last_name: Attendee's last name
            email: Attendee's email address
            
        Returns:
            dict: Registration response including join_url, registrant_id, etc.
        """
        registrant_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email
        }
        
        endpoint = f"/webinars/{webinar_id}/registrants"
        try:
            response = self._make_api_request('POST', endpoint, registrant_data)
            return {
                'success': True,
                'registrant_id': response.get('registrant_id'),
                'join_url': response.get('join_url'),
                'invite_link': response.get('registrant_url', response.get('join_url', '')),
                'zoom_response': response
            }
        except ZoomAPIError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_meeting(self, topic, start_time, duration=30, agenda="", attendee_email=None, attendee_name=None):
        """
        Create a Zoom meeting for clinic sessions.
        
        Args:
            topic: Meeting title/topic
            start_time: datetime object for meeting start
            duration: Meeting duration in minutes (default 30)
            agenda: Meeting agenda/description
            attendee_email: Email of the primary attendee
            attendee_name: Name of the primary attendee
            
        Returns:
            dict: Meeting data including meeting_id, join_url, etc.
        """
        # Prepare meeting data
        meeting_data = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration": duration,
            "timezone": "Europe/London",
            "agenda": agenda,
            "settings": {
                "host_video": True,
                "participant_video": True,
                "cn_meeting": False,
                "in_meeting": False,
                "join_before_host": False,
                "mute_upon_entry": True,
                "watermark": False,
                "use_pmi": False,
                "approval_type": 0,  # Automatically approve
                "audio": "both",
                "auto_recording": "none",
                "enforce_login": False,
                "waiting_room": True,
                "allow_multiple_devices": True
            }
        }
        
        try:
            # Use 'me' to get the current authenticated user
            user_response = self._make_api_request('GET', '/users/me')
            user_id = user_response['id']
            
            # Create the meeting
            endpoint = f"/users/{user_id}/meetings"
            meeting_response = self._make_api_request('POST', endpoint, meeting_data)
            
            return {
                'success': True,
                'meeting_id': str(meeting_response['id']),
                'join_url': meeting_response['join_url'],
                'start_url': meeting_response['start_url'],
                'password': meeting_response.get('password', ''),
                'zoom_response': meeting_response
            }
            
        except ZoomAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'meeting_id': None,
                'join_url': None
            }
    
    def test_connection(self):
        """Test the Zoom API connection and return account info."""
        try:
            response = self._make_api_request('GET', '/accounts/me')
            return {
                'success': True,
                'account_name': response.get('account_name', 'Unknown'),
                'account_id': response.get('account_id', 'Unknown'),
                'message': 'Connection successful'
            }
        except ZoomAPIError as e:
            return {
                'success': False,
                'message': str(e)
            }