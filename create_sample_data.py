import os
import sys
import django
import random
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kajabi_project.settings')
django.setup()

from webinars.models import Webinar, WebinarDate, Attendee

def generate_sample_data():
    """Generate sample data for testing"""
    
    print("Generating sample data...")
    
    # Create sample webinars
    webinars = [
        {
            'name': 'Introduction to Python Programming',
            'kajabi_grant_activation_hook_url': 'https://example.com/kajabi/hooks/python-intro'
        },
        {
            'name': 'Advanced Django Development',
            'kajabi_grant_activation_hook_url': 'https://example.com/kajabi/hooks/django-advanced'
        },
        {
            'name': 'Web Security Best Practices',
            'kajabi_grant_activation_hook_url': 'https://example.com/kajabi/hooks/web-security'
        }
    ]
    
    created_webinars = []
    for webinar_data in webinars:
        webinar, created = Webinar.objects.get_or_create(
            name=webinar_data['name'],
            defaults={'kajabi_grant_activation_hook_url': webinar_data['kajabi_grant_activation_hook_url']}
        )
        created_webinars.append(webinar)
        status = "Created" if created else "Already exists"
        print(f"{status}: Webinar '{webinar.name}'")
    
    # Create sample webinar dates
    now = datetime.now()
    
    for webinar in created_webinars:
        # Create dates in the future
        for i in range(1, 4):
            date_time = now + timedelta(days=i * 7)  # Weekly webinars
            
            webinar_date, created = WebinarDate.objects.get_or_create(
                webinar=webinar,
                date_time=date_time,
                defaults={'zoom_meeting_id': f'zoom-{webinar.id}-{i}' if i % 2 == 0 else None}
            )
            
            status = "Created" if created else "Already exists"
            print(f"{status}: Webinar Date '{webinar.name}' on {date_time.strftime('%Y-%m-%d %H:%M')}")
            
            # Add some attendees to each date
            if created:
                for j in range(1, random.randint(3, 8)):
                    attendee = Attendee.objects.create(
                        webinar_date=webinar_date,
                        first_name=f"Attendee{j}",
                        last_name=f"Sample{j}",
                        email=f"attendee{j}_{webinar_date.id}@example.com"
                    )
                    print(f"Created: Attendee '{attendee.first_name} {attendee.last_name}' for '{webinar.name}' on {date_time.strftime('%Y-%m-%d')}")
    
    print("\nSample data generation complete!")


if __name__ == '__main__':
    generate_sample_data()