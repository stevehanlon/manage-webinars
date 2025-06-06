from django.core.management.base import BaseCommand
from django.utils import timezone
from webinars.models import Attendee, OnDemandAttendee, BundleAttendee, Download
from webinars.salesforce_service import SalesforceService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync pending attendees and downloads to Salesforce'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of attendees and downloads to process in this run'
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
        
        # Collect all pending attendees and downloads from different models
        pending_items = []
        
        # Get pending regular attendees
        regular_attendees = Attendee.objects.filter(
            deleted_at=None,
            salesforce_sync_pending=True
        ).select_related('webinar_date__webinar')[:limit]
        
        for attendee in regular_attendees:
            pending_items.append(('Attendee', attendee))
        
        # Get pending on-demand attendees
        if len(pending_items) < limit:
            remaining = limit - len(pending_items)
            ondemand_attendees = OnDemandAttendee.objects.filter(
                deleted_at=None,
                salesforce_sync_pending=True
            ).select_related('webinar')[:remaining]
            
            for attendee in ondemand_attendees:
                pending_items.append(('OnDemandAttendee', attendee))
        
        # Get pending bundle attendees
        if len(pending_items) < limit:
            remaining = limit - len(pending_items)
            bundle_attendees = BundleAttendee.objects.filter(
                deleted_at=None,
                salesforce_sync_pending=True
            ).select_related('bundle_date__bundle')[:remaining]
            
            for attendee in bundle_attendees:
                pending_items.append(('BundleAttendee', attendee))
        
        # Get pending downloads
        if len(pending_items) < limit:
            remaining = limit - len(pending_items)
            downloads = Download.objects.filter(
                deleted_at=None,
                salesforce_sync_pending=True
            )[:remaining]
            
            for download in downloads:
                pending_items.append(('Download', download))
        
        if not pending_items:
            self.stdout.write(self.style.SUCCESS('No attendees or downloads pending Salesforce sync'))
            return
        
        self.stdout.write(f'Found {len(pending_items)} items pending sync')
        
        success_count = 0
        error_count = 0
        
        for item_type, item in pending_items:
            try:
                if dry_run:
                    if item_type == 'Download':
                        self.stdout.write(
                            f'[DRY RUN] Would sync {item_type}: {item.first_name} {item.last_name} '
                            f'({item.email}) - {item.form_title}'
                        )
                    else:
                        webinar_name = self._get_webinar_name(item)
                        self.stdout.write(
                            f'[DRY RUN] Would sync {item_type}: {item.first_name} {item.last_name} '
                            f'({item.email}) - {webinar_name}'
                        )
                    if item.organization:
                        self.stdout.write(f'  Organization: {item.organization}')
                    continue
                
                # Attempt to sync to Salesforce
                if item_type == 'Download':
                    success, message = sf_service.sync_download(item)
                else:
                    success, message = sf_service.sync_attendee(item)
                
                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Synced {item_type}: {item.first_name} {item.last_name} ({item.email})'
                        )
                    )
                else:
                    error_count += 1
                    # Update item with error
                    item.salesforce_sync_error = message
                    item.salesforce_sync_pending = True  # Keep it pending for retry
                    item.save()
                    
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Failed to sync {item_type}: {item.first_name} {item.last_name} '
                            f'({item.email}) - {message}'
                        )
                    )
                    
            except Exception as e:
                error_count += 1
                error_msg = f"Unexpected error: {str(e)}"
                
                if not dry_run:
                    item.salesforce_sync_error = error_msg
                    item.salesforce_sync_pending = True  # Keep it pending for retry
                    item.save()
                
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Exception syncing {item_type}: {item.first_name} {item.last_name} '
                        f'({item.email}) - {error_msg}'
                    )
                )
                logger.exception(f"Error syncing {item_type} {item.id} to Salesforce")
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN COMPLETE: Would process {len(pending_items)} items')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'SYNC COMPLETE: {success_count} successful, {error_count} failed'
                )
            )
            
            if success_count > 0:
                self.stdout.write(f'Successfully synced {success_count} items to Salesforce')
            
            if error_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'{error_count} items failed to sync. Check logs for details. '
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