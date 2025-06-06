import logging
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional
from django.utils import timezone as django_timezone

logger = logging.getLogger(__name__)


class SalesforceService:
    """Service for integrating with Salesforce API using simple-salesforce."""
    
    def __init__(self):
        self.sf = None
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
    
    def _connect(self) -> bool:
        """Connect to Salesforce using simple-salesforce."""
        if not self.settings:
            logger.error("No Salesforce settings available")
            return False
        
        try:
            from simple_salesforce import Salesforce
            
            # Connect to Salesforce
            # Start with the simplest approach - let simple-salesforce handle the domain
            logger.info(f"Attempting to connect to Salesforce with username: {self.settings.username}")
            
            self.sf = Salesforce(
                username=self.settings.username,
                password=self.settings.password,
                security_token=self.settings.security_token
                # Don't specify domain initially - let simple-salesforce auto-detect
            )
            
            logger.info("Successfully connected to Salesforce")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to Salesforce: {str(e)}")
            return False
    
    def find_account_by_name(self, account_name: str) -> Optional[str]:
        """Find Account by name, return Account ID if found."""
        if not account_name:
            return None
        
        if not self.sf and not self._connect():
            return None
        
        try:
            # Query for account by name
            escaped_name = account_name.replace("'", "\\'")
            query = f"SELECT Id FROM Account WHERE Name = '{escaped_name}'"
            result = self.sf.query(query)
            
            if result['records']:
                return result['records'][0]['Id']
            return None
            
        except Exception as e:
            logger.error(f"Error finding account by name: {str(e)}")
            return None
    
    def create_account(self, account_name: str) -> Tuple[bool, str, str]:
        """Create a new Account in Salesforce."""
        if not account_name:
            return False, "", "No account name provided"
        
        if not self.sf and not self._connect():
            return False, "", "Failed to connect to Salesforce"
        
        try:
            account_data = {
                'Name': account_name,
                'Type': 'Customer'  # Set Account Type to Customer
            }
            
            result = self.sf.Account.create(account_data)
            
            if result['success']:
                logger.info(f"Created Account: {account_name} (ID: {result['id']})")
                return True, result['id'], f"Created Account: {account_name}"
            else:
                logger.error(f"Failed to create Account: {result}")
                return False, "", f"Failed to create Account: {result}"
                
        except Exception as e:
            logger.error(f"Error creating account: {str(e)}")
            return False, "", f"Error creating account: {str(e)}"
    
    def find_contact_by_email(self, email: str) -> Optional[str]:
        """Find Contact by email, return Contact ID if found."""
        if not email:
            return None
        
        if not self.sf and not self._connect():
            return None
        
        try:
            # Query for contact by email
            escaped_email = email.replace("'", "\\'")
            query = f"SELECT Id FROM Contact WHERE Email = '{escaped_email}'"
            result = self.sf.query(query)
            
            if result['records']:
                return result['records'][0]['Id']
            return None
            
        except Exception as e:
            logger.error(f"Error finding contact by email: {str(e)}")
            return None
    
    def create_contact(self, first_name: str, last_name: str, email: str, account_id: str = None) -> Tuple[bool, str, str]:
        """Create a new Contact in Salesforce."""
        if not email:
            return False, "", "No email provided"
        
        if not self.sf and not self._connect():
            return False, "", "Failed to connect to Salesforce"
        
        try:
            # Start with required fields only
            contact_data = {
                'FirstName': first_name,
                'LastName': last_name or 'Unknown',  # LastName is required
                'Email': email
            }
            
            # Add Account association if provided
            if account_id:
                contact_data['AccountId'] = account_id
            
            # Add custom fields (if they don't exist, Salesforce will ignore them)
            contact_data['In_Mailchimp__c'] = True
            contact_data['Opted_IN__c'] = True
            
            logger.info(f"Creating contact with data: {contact_data}")
            result = self.sf.Contact.create(contact_data)
            
            if result['success']:
                logger.info(f"Created Contact: {first_name} {last_name} (ID: {result['id']})")
                return True, result['id'], f"Created Contact: {first_name} {last_name}"
            else:
                logger.error(f"Failed to create Contact: {result}")
                return False, "", f"Failed to create Contact: {result}"
                
        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}")
            return False, "", f"Error creating contact: {str(e)}"
    
    def create_task(self, contact_id: str, subject: str, description: str) -> Tuple[bool, str, str]:
        """Create a completed Task in Salesforce assigned to Rachel CLINTON."""
        if not contact_id:
            return False, "", "No contact ID provided"
        
        if not self.sf and not self._connect():
            return False, "", "Failed to connect to Salesforce"
        
        try:
            # Rachel CLINTON's User ID
            assigned_to_id = "0054J000002nMfC"
            
            # Start with minimal required fields
            task_data = {
                'WhoId': contact_id,  # Contact the task is related to
                'OwnerId': assigned_to_id,  # User the task is assigned to
                'Subject': subject,
                'Status': 'Completed'  # Task is completed
            }
            
            # Add optional fields safely
            if description:
                task_data['Description'] = description
                
            # Try to add ActivityDate (some orgs might restrict this)
            try:
                task_data['ActivityDate'] = datetime.now().date().isoformat()
            except:
                pass  # Skip if not allowed
            
            logger.info(f"Creating task with data: {task_data}")
            result = self.sf.Task.create(task_data)
            
            if result['success']:
                logger.info(f"Created Task: {subject} (ID: {result['id']})")
                return True, result['id'], f"Created Task: {subject}"
            else:
                logger.error(f"Failed to create Task: {result}")
                return False, "", f"Failed to create Task: {result}"
                
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return False, "", f"Error creating task: {str(e)}"
    
    def sync_attendee(self, attendee) -> Tuple[bool, str]:
        """Sync an attendee to Salesforce (Account, Contact, Task)."""
        try:
            # Step 1: Handle Account (Organization)
            account_id = None
            if attendee.organization:
                # Try to find existing account
                account_id = self.find_account_by_name(attendee.organization)
                
                if not account_id:
                    # Create new account
                    success, account_id, message = self.create_account(attendee.organization)
                    if not success:
                        return False, f"Failed to create account: {message}"
            
            # Step 2: Handle Contact
            contact_id = self.find_contact_by_email(attendee.email)
            
            if not contact_id:
                # Create new contact
                success, contact_id, message = self.create_contact(
                    attendee.first_name, 
                    attendee.last_name, 
                    attendee.email, 
                    account_id
                )
                if not success:
                    return False, f"Failed to create contact: {message}"
            
            # Step 3: Create Task
            webinar_name = self._get_webinar_name(attendee)
            task_subject = f"Webinar Registration: {webinar_name}"
            task_description = f"Contact registered for webinar: {webinar_name}\nEmail: {attendee.email}"
            if attendee.organization:
                task_description += f"\nOrganization: {attendee.organization}"
            
            success, task_id, message = self.create_task(contact_id, task_subject, task_description)
            if not success:
                return False, f"Failed to create task: {message}"
            
            # Step 4: Update attendee with Salesforce IDs
            attendee.salesforce_contact_id = contact_id
            attendee.salesforce_account_id = account_id or ""  # Handle None case
            attendee.salesforce_task_id = task_id
            attendee.salesforce_synced_at = django_timezone.now()
            attendee.salesforce_sync_pending = False
            attendee.salesforce_sync_error = ""
            attendee.save()
            
            logger.info(f"Successfully synced attendee {attendee.email} to Salesforce")
            return True, f"Successfully synced to Salesforce"
            
        except Exception as e:
            error_msg = f"Error syncing attendee to Salesforce: {str(e)}"
            logger.error(error_msg)
            
            # Update attendee with error
            attendee.salesforce_sync_error = error_msg
            attendee.salesforce_sync_pending = True  # Keep pending for retry
            attendee.save()
            
            return False, error_msg
    
    def sync_download(self, download) -> Tuple[bool, str]:
        """Sync a download to Salesforce (Account, Contact, Task)."""
        try:
            # Step 1: Handle Account (Organization)
            account_id = None
            if download.organization:
                # Try to find existing account
                account_id = self.find_account_by_name(download.organization)
                
                if not account_id:
                    # Create new account
                    success, account_id, message = self.create_account(download.organization)
                    if not success:
                        return False, f"Failed to create account: {message}"
            
            # Step 2: Handle Contact
            contact_id = self.find_contact_by_email(download.email)
            
            if not contact_id:
                # Create new contact
                success, contact_id, message = self.create_contact(
                    download.first_name, 
                    download.last_name, 
                    download.email, 
                    account_id
                )
                if not success:
                    return False, f"Failed to create contact: {message}"
            
            # Step 3: Create Task for download
            task_subject = f"Download: {download.form_title}"
            task_description = f"Contact downloaded resource: {download.form_title}\nEmail: {download.email}"
            if download.organization:
                task_description += f"\nOrganization: {download.organization}"
            
            success, task_id, message = self.create_task(contact_id, task_subject, task_description)
            if not success:
                return False, f"Failed to create task: {message}"
            
            # Step 4: Update download with Salesforce IDs
            download.salesforce_contact_id = contact_id
            download.salesforce_account_id = account_id or ""  # Handle None case
            download.salesforce_task_id = task_id
            download.salesforce_synced_at = django_timezone.now()
            download.salesforce_sync_pending = False
            download.salesforce_sync_error = ""
            download.save()
            
            logger.info(f"Successfully synced download {download.email} to Salesforce")
            return True, f"Successfully synced to Salesforce"
            
        except Exception as e:
            error_msg = f"Error syncing download to Salesforce: {str(e)}"
            logger.error(error_msg)
            
            # Update download with error
            download.salesforce_sync_error = error_msg
            download.salesforce_sync_pending = True  # Keep pending for retry
            download.save()
            
            return False, error_msg
    
    def _get_webinar_name(self, attendee):
        """Get webinar name based on attendee type."""
        if hasattr(attendee, 'webinar_date') and attendee.webinar_date:
            return attendee.webinar_date.webinar.name
        elif hasattr(attendee, 'webinar') and attendee.webinar:
            return attendee.webinar.name
        elif hasattr(attendee, 'bundle_date') and attendee.bundle_date:
            return attendee.bundle_date.bundle.name
        else:
            return "Unknown Webinar"