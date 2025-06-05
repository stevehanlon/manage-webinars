import logging
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional
import requests
import base64

logger = logging.getLogger(__name__)


class SalesforceService:
    """Service for integrating with Salesforce API."""
    
    def __init__(self):
        self.access_token = None
        self.instance_url = None
        self._load_settings()
    
    def _load_settings(self):
        """Load Salesforce settings from database."""
        try:
            from settings.models import SalesforceSettings
            self.settings = SalesforceSettings.objects.first()
            if not self.settings:
                raise Exception("No Salesforce settings found")
        except Exception as e:
            logger.error(f"Failed to load Salesforce settings: {str(e)}")
            self.settings = None
    
    def _authenticate(self) -> bool:
        """Authenticate with Salesforce and get access token."""
        if not self.settings:
            logger.error("No Salesforce settings available")
            return False
        
        # Salesforce OAuth2 password flow
        auth_url = f"https://{self.settings.subdomain}.my.salesforce.com/services/oauth2/token"
        
        data = {
            'grant_type': 'password',
            'client_id': '3MVG9A2kN3Bn17hsdQNI4Q', # Default connected app client ID (placeholder)
            'client_secret': 'your_client_secret',  # You'll need to configure this
            'username': self.settings.username,
            'password': f"{self.settings.password}{self.settings.security_token}"
        }
        
        try:
            response = requests.post(auth_url, data=data)
            if response.status_code == 200:
                auth_data = response.json()
                self.access_token = auth_data['access_token']
                self.instance_url = auth_data['instance_url']
                logger.info("Successfully authenticated with Salesforce")
                return True
            else:
                logger.error(f"Salesforce authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error authenticating with Salesforce: {str(e)}")
            return False
    
    def _make_request(self, method: str, endpoint: str, data: dict = None) -> Tuple[bool, dict]:
        """Make authenticated request to Salesforce API."""
        if not self.access_token and not self._authenticate():
            return False, {"error": "Authentication failed"}
        
        url = f"{self.instance_url}/services/data/v58.0/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            if response.status_code in [200, 201]:
                return True, response.json()
            elif response.status_code == 401:
                # Token expired, try to re-authenticate
                logger.info("Access token expired, re-authenticating...")
                if self._authenticate():
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    if method.upper() == 'GET':
                        response = requests.get(url, headers=headers)
                    elif method.upper() == 'POST':
                        response = requests.post(url, json=data, headers=headers)
                    elif method.upper() == 'PATCH':
                        response = requests.patch(url, json=data, headers=headers)
                    
                    if response.status_code in [200, 201]:
                        return True, response.json()
            
            logger.error(f"Salesforce API error: {response.status_code} - {response.text}")
            return False, {"error": f"API error: {response.status_code}", "details": response.text}
        
        except Exception as e:
            logger.error(f"Error making Salesforce request: {str(e)}")
            return False, {"error": str(e)}
    
    def find_account_by_name(self, account_name: str) -> Optional[str]:
        """Find Account by name, return Account ID if found."""
        if not account_name:
            return None
        
        # SOQL query to find account by name
        escaped_name = account_name.replace("'", "\\'")
        query = f"SELECT Id FROM Account WHERE Name = '{escaped_name}'"
        success, result = self._make_request('GET', f"query/?q={query}")
        
        if success and result.get('records'):
            return result['records'][0]['Id']
        return None
    
    def create_account(self, account_name: str) -> Tuple[bool, str, str]:
        """Create a new Account in Salesforce."""
        if not account_name:
            return False, "", "No account name provided"
        
        account_data = {
            'Name': account_name,
            'Type': 'Customer'  # Set Account Type to Customer
        }
        
        success, result = self._make_request('POST', 'sobjects/Account/', account_data)
        
        if success:
            account_id = result.get('id')
            logger.info(f"Created Salesforce Account: {account_name} (ID: {account_id})")
            return True, account_id, ""
        else:
            error_msg = f"Failed to create account: {result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def find_contact_by_email(self, email: str) -> Optional[str]:
        """Find Contact by email, return Contact ID if found."""
        if not email:
            return None
        
        # SOQL query to find contact by email
        escaped_email = email.replace("'", "\\'")
        query = f"SELECT Id FROM Contact WHERE Email = '{escaped_email}'"
        success, result = self._make_request('GET', f"query/?q={query}")
        
        if success and result.get('records'):
            return result['records'][0]['Id']
        return None
    
    def create_contact(self, first_name: str, last_name: str, email: str, account_id: str = None) -> Tuple[bool, str, str]:
        """Create a new Contact in Salesforce."""
        contact_data = {
            'FirstName': first_name,
            'LastName': last_name,
            'Email': email,
            'In_Mailchimp__c': True,  # Newsletter checkbox
            'Opted_IN__c': True       # Opted in checkbox
        }
        
        if account_id:
            contact_data['AccountId'] = account_id
        
        success, result = self._make_request('POST', 'sobjects/Contact/', contact_data)
        
        if success:
            contact_id = result.get('id')
            logger.info(f"Created Salesforce Contact: {first_name} {last_name} ({email}) - ID: {contact_id}")
            return True, contact_id, ""
        else:
            error_msg = f"Failed to create contact: {result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def create_task(self, contact_id: str, subject: str, description: str) -> Tuple[bool, str, str]:
        """Create a completed Task in Salesforce."""
        task_data = {
            'Subject': subject,
            'Description': description,
            'WhoId': contact_id,  # Link to Contact
            'Status': 'Completed',
            'Priority': 'Normal',
            'ActivityDate': datetime.now().strftime('%Y-%m-%d'),  # Due date (today)
            'OwnerId': '0054J000002nMfC'  # Assigned to Rachel CLINTON
        }
        
        success, result = self._make_request('POST', 'sobjects/Task/', task_data)
        
        if success:
            task_id = result.get('id')
            logger.info(f"Created Salesforce Task: {subject} (ID: {task_id})")
            return True, task_id, ""
        else:
            error_msg = f"Failed to create task: {result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def sync_attendee(self, attendee) -> Tuple[bool, str]:
        """
        Sync an attendee to Salesforce.
        Creates account (if needed), contact (if needed), and task.
        """
        try:
            account_id = None
            contact_id = None
            task_id = None
            
            # Step 1: Handle organization/account
            if attendee.organization:
                account_id = self.find_account_by_name(attendee.organization)
                if not account_id:
                    success, account_id, error = self.create_account(attendee.organization)
                    if not success:
                        return False, f"Failed to create account: {error}"
            
            # Step 2: Handle contact
            contact_id = self.find_contact_by_email(attendee.email)
            if not contact_id:
                success, contact_id, error = self.create_contact(
                    attendee.first_name, 
                    attendee.last_name, 
                    attendee.email, 
                    account_id
                )
                if not success:
                    return False, f"Failed to create contact: {error}"
            
            # Step 3: Create task
            webinar_name = self._get_webinar_name(attendee)
            task_description = self._build_task_description(attendee)
            
            success, task_id, error = self.create_task(
                contact_id, 
                f"Webinar Registration: {webinar_name}", 
                task_description
            )
            if not success:
                return False, f"Failed to create task: {error}"
            
            # Step 4: Update attendee with Salesforce IDs
            attendee.salesforce_contact_id = contact_id
            attendee.salesforce_account_id = account_id
            attendee.salesforce_task_id = task_id
            attendee.salesforce_synced_at = datetime.now(timezone.utc)
            attendee.salesforce_sync_pending = False
            attendee.salesforce_sync_error = ""
            attendee.save()
            
            logger.info(f"Successfully synced attendee {attendee.email} to Salesforce")
            return True, "Successfully synced to Salesforce"
            
        except Exception as e:
            error_msg = f"Error syncing attendee to Salesforce: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _get_webinar_name(self, attendee) -> str:
        """Get webinar name based on attendee type."""
        if hasattr(attendee, 'webinar_date'):
            return attendee.webinar_date.webinar.name
        elif hasattr(attendee, 'webinar'):
            return attendee.webinar.name
        elif hasattr(attendee, 'bundle_date'):
            return attendee.bundle_date.bundle.name
        else:
            return "Unknown Webinar"
    
    def _build_task_description(self, attendee) -> str:
        """Build task description with attendee details."""
        lines = [
            f"Attendee: {attendee.first_name} {attendee.last_name}",
            f"Email: {attendee.email}",
        ]
        
        if attendee.organization:
            lines.append(f"Organization: {attendee.organization}")
        
        if hasattr(attendee, 'webinar_date'):
            if attendee.webinar_date.on_demand:
                lines.append("Type: On-Demand Webinar")
            else:
                lines.append(f"Scheduled Date: {attendee.webinar_date.date_time.strftime('%Y-%m-%d %H:%M')}")
        elif hasattr(attendee, 'webinar'):
            lines.append("Type: On-Demand Webinar")
        elif hasattr(attendee, 'bundle_date'):
            lines.append(f"Bundle Date: {attendee.bundle_date.date}")
        
        lines.append(f"Registered: {attendee.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        return "\\n".join(lines)