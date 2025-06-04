# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a Django application for managing registrations to webinars from Kajabi and then granting access at a later date.

## Development Environment
- Python virtual environment (venv) is used for package management
- Django 5.2.1 is the web framework
- MySQL is used for the database
- Bootstrap 5 for frontend styling
- Django REST Framework for API endpoints

## Common Commands
- Setup the development environment:
  ```bash
  python -m venv venv
  source venv/bin/activate
  pip install django mysqlclient djangorestframework django-bootstrap5
  ```

- Run the Django development server:
  ```bash
  python manage.py runserver
  ```

- Apply database migrations:
  ```bash
  python manage.py migrate
  ```

- Create new migrations:
  ```bash
  python manage.py makemigrations
  ```

- Create initial admin user:
  ```bash
  python create_admin.py
  ```

- Run tests:
  ```bash
  python manage.py test
  ```

## Database Configuration
- Database Name: kajabi
- Username: kajabi
- Password: gokajabi
- Host: localhost
- Port: 3306

## Project Structure
- kajabi_project/: Main Django project settings
- webinars/: Core app for webinar management
  - models.py: Defines Webinar, WebinarDate, and Attendee models
  - views.py: Contains views for the webinar dashboard and CRUD operations
  - forms.py: Form definitions for webinar management
  - api.py: REST API viewsets
  - serializers.py: Django REST Framework serializers
  - zoom_service.py: Zoom API integration service
- accounts/: App for user authentication and management
- settings/: App for system configuration
  - models.py: Defines ZoomSettings model for API credentials
  - views.py: Settings dashboard and configuration views
- templates/: HTML templates organized by app
- static/: Static assets (CSS, JS)

## Important Models
- Webinar: Represents a webinar series
- WebinarDate: A specific date for a webinar
- Attendee: A person registered for a specific webinar date

## API Endpoints
- `/api/webinars/`: Webinar management
- `/api/webinar-dates/`: Webinar date management
- `/api/attendees/`: Attendee management
- `/api/attendee-webhook/`: Webhook for registering attendees

### Kajabi Webhook Integration
The webhook at `/api/attendee-webhook/` supports two types of Kajabi events:

1. Form submissions (`form_submission.created`):
   - Matches webinar by form title
   - Extracts date from the field specified in webinar.form_date_field
   - Extracts name and email from the payload

2. Purchase events (`purchase.created`):
   - Matches webinar by offer title
   - Extracts date from the field specified in webinar.checkout_date_field
   - Extracts name and email from member information

The webhook includes error handling with email notifications to the address specified in each webinar's error_notification_email field.

## Zoom Integration
The application includes Zoom API integration for automatically creating meetings:

### Configuration
- Access Settings -> Zoom Settings to configure API credentials
- Required: Client ID, Client Secret, Account ID (from Zoom Server-to-Server OAuth App)
- Optional: Webinar Template ID for consistent webinar settings

### Features
- Automatic Zoom webinar creation for webinar dates
- Test connection functionality to verify API credentials
- Integration with existing "Create Zoom" buttons in webinar management

### Setup Requirements
1. Create a Zoom Server-to-Server OAuth App at https://marketplace.zoom.us/
2. Add required scopes: `webinar:write` and `user:read`
3. Configure credentials in the Settings -> Zoom Settings page
4. Test connection to verify setup

## Salesforce Integration
The application includes configuration for future Salesforce API integration:

### Configuration
- Access Settings -> Salesforce Settings to configure API credentials
- Required: Subdomain, Username, Password, Security Token

### Setup Requirements
1. Log into your Salesforce org
2. Go to Setup → Users → Users and click on your user profile
3. Click "Reset My Security Token" to get your security token
4. Check your email for the security token
5. For subdomain, use the part before .salesforce.com in your org URL
6. Configure credentials in the Settings -> Salesforce Settings page

### Note
These settings prepare the system for future Salesforce integrations with webinar attendee data. No active integration is currently implemented.

## MS365 Calendar Integration
The application includes Microsoft 365 calendar integration for automatically sending calendar invites when webinar dates are created:

### Configuration
- Access Settings -> MS365 Settings to configure API credentials
- Required: Client ID, Client Secret, Tenant ID (from Azure App Registration)
- Owner Email: Calendar where meetings will be created

### Features
- Automatic calendar invites when dates are auto-created from Kajabi webhooks
- Invites sent to all users in the "calendar" Django group
- Auto-created dates marked with [AUTO-CREATED] prefix
- Integration with webinar and bundle dates

### Setup Requirements
1. Create an Azure App Registration at https://portal.azure.com
2. Add required permissions: `Calendars.ReadWrite` and `User.Read`
3. Configure credentials in the Settings -> MS365 Settings page
4. Create "calendar" group: `python manage.py create_calendar_group`
5. Add users to the calendar group via Django admin

### Calendar Group Management
- Users must be in the "calendar" group to receive invites
- Only users with email addresses will receive invites
- Manage group membership in Django Admin -> Groups -> calendar

## Important Notes
- The README.md should be kept up to date as functionality is added to the project
- Document API integrations with Kajabi as they are implemented
- Zoom webinars are created using the Zoom API when users click "Create Zoom" on webinar dates
- Admin user is created with username "attadmin" and initial password "temporary_password"