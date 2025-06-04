from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Creates the calendar group for users who should receive calendar invites'

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name='calendar')
        
        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created calendar group'))
        else:
            self.stdout.write(self.style.WARNING('Calendar group already exists'))
            
        self.stdout.write(self.style.NOTICE(
            'Add users to this group through the Django admin to have them receive calendar invites'
        ))