# Kajabi Webinar Manager

A Django application for managing registrations to webinars from Kajabi and granting access at a later date.

## Project Overview

The Kajabi Webinar Manager is a web application that allows you to:

- Manage webinar series and specific dates
- Track attendee registrations
- Create Zoom meetings for webinars
- Grant Kajabi access via webhooks

## Key Features

- User authentication and management
- Dashboard with webinar overview
- Webinar CRUD operations
- Webinar date management
- Attendee tracking
- Zoom integration (planned)
- Kajabi integration via webhooks

## Technology Stack

- Django 5.2.1
- MySQL database
- Bootstrap 5 for frontend styling
- Django REST Framework for API endpoints

## Installation and Setup

### Prerequisites

- Python 3.13+
- MySQL 8.0+
- pip and virtualenv

### Database Setup

The application requires a MySQL database with the following configuration:

```sql
CREATE DATABASE kajabi;
CREATE USER kajabi@localhost IDENTIFIED BY 'gokajabi';
GRANT ALL PRIVILEGES ON kajabi.* TO kajabi@localhost;
```

### Installation Steps

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd kajabi2
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install django mysqlclient djangorestframework django-bootstrap5
   ```

4. Apply database migrations:
   ```bash
   python manage.py migrate
   ```

5. Create an admin user:
   ```bash
   python create_admin.py
   ```

6. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Admin User Setup

A script is provided to create the admin user:

- Username: attadmin
- Initial password: temporary_password

After creating the admin user, you should log in to the admin interface at `/admin` and change the password immediately.

## API Endpoints

The application provides REST API endpoints for:

- `/api/webinars/` - Webinar management
- `/api/webinar-dates/` - Webinar date management
- `/api/attendees/` - Attendee management

A webhook endpoint is available for registering attendees:

- `/api/attendee-webhook/` - Register attendees via POST requests

### Kajabi Webhook Integration

The system supports automatic registration of attendees via Kajabi webhooks. It handles two types of Kajabi events:

1. **Form Submission Events** (`form_submission.created`)
   ```json
   {
     "id": "0a49a63a-30b3-11f0-a9e9-072cd5d18f1b",
     "event": "form_submission.created",
     "payload": {
       "First Name": "John",
       "Email": "john@example.com",
       "Webinar options": "21 August, 10-11:00 BST",
       "form_title": "Getting started with WordPress multiple dates"
     }
   }
   ```

2. **Purchase Events** (`purchase.created`)
   ```json
   {
     "id": "058d8e00-30d0-11f0-a9de-4760263d74c0",
     "event": "purchase.created",
     "payload": {
       "offer_title": "Getting started with wordpress paid",
       "member_email": "john@example.com",
       "member_first_name": "John",
       "member_last_name": "Doe",
       "custom_field_getting_started_with_wordpress_dates": "19 June, 10-11:00 BST"
     }
   }
   ```

The webhook automatically:
- Matches the webinar by form title or offer title
- Parses the date string to find the correct webinar date
- Registers the attendee for the matching webinar date

### Direct API Integration

For direct integration, send a POST request with:
```json
{
  "webinar_date_id": 123,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com"
}
```

## Development

### Running Tests

```bash
python manage.py test
```

### Generating Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## License

[Specify your license here]