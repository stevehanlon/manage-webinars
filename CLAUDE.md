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
- accounts/: App for user authentication and management
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

## Important Notes
- The README.md should be kept up to date as functionality is added to the project
- Document API integrations with Kajabi as they are implemented
- Future Zoom integration will need to be implemented in the WebinarDate model
- Admin user is created with username "attadmin" and initial password "temporary_password"