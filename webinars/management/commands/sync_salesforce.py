from django.core.management.base import BaseCommand
from django.utils import timezone
from webinars.models import Attendee, OnDemandAttendee, BundleAttendee
from webinars.salesforce_service import SalesforceService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync pending attendees to Salesforce'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of attendees to process in this run'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Initialize Salesforce service
        sf_service = SalesforceService()
        
        # Collect all pending attendees from different models
        pending_attendees = []
        
        # Get pending regular attendees
        regular_attendees = Attendee.objects.filter(
            deleted_at=None,
            salesforce_sync_pending=True
        ).select_related('webinar_date__webinar')[:limit]
        
        for attendee in regular_attendees:
            pending_attendees.append(('Attendee', attendee))
        
        # Get pending on-demand attendees
        if len(pending_attendees) < limit:
            remaining = limit - len(pending_attendees)
            ondemand_attendees = OnDemandAttendee.objects.filter(
                deleted_at=None,
                salesforce_sync_pending=True
            ).select_related('webinar')[:remaining]
            
            for attendee in ondemand_attendees:
                pending_attendees.append(('OnDemandAttendee', attendee))
        
        # Get pending bundle attendees
        if len(pending_attendees) < limit:
            remaining = limit - len(pending_attendees)
            bundle_attendees = BundleAttendee.objects.filter(
                deleted_at=None,
                salesforce_sync_pending=True
            ).select_related('bundle_date__bundle')[:remaining]
            
            for attendee in bundle_attendees:
                pending_attendees.append(('BundleAttendee', attendee))
        
        if not pending_attendees:
            self.stdout.write(self.style.SUCCESS('No attendees pending Salesforce sync'))
            return
        
        self.stdout.write(f'Found {len(pending_attendees)} attendees pending sync')
        
        success_count = 0
        error_count = 0
        
        for attendee_type, attendee in pending_attendees:
            try:
                if dry_run:
                    webinar_name = self._get_webinar_name(attendee)
                    self.stdout.write(
                        f'[DRY RUN] Would sync {attendee_type}: {attendee.first_name} {attendee.last_name} '
                        f'({attendee.email}) - {webinar_name}'
                    )
                    if attendee.organization:
                        self.stdout.write(f'  Organization: {attendee.organization}')
                    continue
                
                # Attempt to sync to Salesforce
                success, message = sf_service.sync_attendee(attendee)
                
                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Synced {attendee_type}: {attendee.first_name} {attendee.last_name} ({attendee.email})'
                        )
                    )
                else:
                    error_count += 1
                    # Update attendee with error
                    attendee.salesforce_sync_error = message
                    attendee.salesforce_sync_pending = True  # Keep it pending for retry
                    attendee.save()
                    
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Failed to sync {attendee_type}: {attendee.first_name} {attendee.last_name} '
                            f'({attendee.email}) - {message}'
                        )
                    )
                    
            except Exception as e:
                error_count += 1
                error_msg = f"Unexpected error: {str(e)}"
                
                if not dry_run:
                    attendee.salesforce_sync_error = error_msg
                    attendee.salesforce_sync_pending = True  # Keep it pending for retry
                    attendee.save()
                
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Exception syncing {attendee_type}: {attendee.first_name} {attendee.last_name} '
                        f'({attendee.email}) - {error_msg}'
                    )
                )
                logger.exception(f"Error syncing attendee {attendee.id} to Salesforce")
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN COMPLETE: Would process {len(pending_attendees)} attendees')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'SYNC COMPLETE: {success_count} successful, {error_count} failed'
                )
            )
            
            if success_count > 0:
                self.stdout.write(f'Successfully synced {success_count} attendees to Salesforce')
            
            if error_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'{error_count} attendees failed to sync. Check logs for details. '
                        'They will be retried on the next run.'
                    )
                )
    
    def _get_webinar_name(self, attendee):
        """Get webinar name based on attendee type."""
        if hasattr(attendee, 'webinar_date'):
            return attendee.webinar_date.webinar.name
        elif hasattr(attendee, 'webinar'):
            return attendee.webinar.name
        elif hasattr(attendee, 'bundle_date'):
            return attendee.bundle_date.bundle.name
        else:
            return "Unknown Webinar"