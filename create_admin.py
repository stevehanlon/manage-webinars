import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kajabi_project.settings')
django.setup()

from django.contrib.auth.models import User
from django.db.utils import IntegrityError

def create_admin_user():
    """Create the admin user if it doesn't already exist."""
    
    username = 'attadmin'
    
    try:
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"Admin user '{username}' already exists.")
            return
        
        # Create a new admin user with a temporary password
        admin = User.objects.create_superuser(
            username=username,
            email='admin@example.com',
            password='temporary_password'
        )
        print(f"Admin user '{username}' created successfully!")
        print(f"Username: {username}")
        print("Password: temporary_password")
        print("\nIMPORTANT: Please login and change the password immediately for security reasons.")
        
    except IntegrityError:
        print(f"Error: Could not create admin user '{username}'.")
        print("It's possible that the user already exists but with a different case.")
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")

if __name__ == '__main__':
    create_admin_user()