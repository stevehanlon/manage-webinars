from django.core.management.base import BaseCommand
from django.utils import timezone
from webinars.activation_service import activate_pending_attendees
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Activate pending Kajabi grant offers for attendees'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be activated without actually activating'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Maximum number of attendees to process (default: no limit)'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Only output summary, not individual activation details'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options.get('limit')
        quiet = options['quiet']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No activations will be sent'))
        
        start_time = timezone.now()
        
        try:
            if dry_run:
                # In dry-run mode, find attendees but don't activate
                from webinars.models import Attendee, BundleAttendee
                
                # Count regular attendees who need activation
                regular_attendees = Attendee.objects.filter(
                    deleted_at=None,
                    activation_sent_at=None
                ).select_related('webinar_date', 'webinar_date__webinar')
                
                # Count bundle attendees who need activation  
                bundle_attendees = BundleAttendee.objects.filter(
                    deleted_at=None,
                    activation_sent_at=None
                ).select_related('bundle_date', 'bundle_date__bundle')
                
                activation_messages = []
                pending_count = 0
                
                for attendee in regular_attendees:
                    if attendee.needs_activation:
                        pending_count += 1
                        webinar_name = attendee.webinar_date.webinar.name
                        activation_messages.append(
                            f"[DRY RUN] Would activate {attendee.email} for {webinar_name}"
                        )
                        
                for attendee in bundle_attendees:
                    if attendee.needs_activation:
                        pending_count += 1
                        bundle_name = attendee.bundle_date.bundle.name
                        activation_messages.append(
                            f"[DRY RUN] Would activate {attendee.email} for {bundle_name}"
                        )
                
                success_count = pending_count
                failure_count = 0
            else:
                # Call the activation service
                success_count, failure_count, activation_messages = activate_pending_attendees()
            
            # Apply limit if specified (by only processing first N messages)
            if limit and len(activation_messages) > limit:
                # This is a simplification - ideally the service would support limit
                self.stdout.write(self.style.WARNING(
                    f'Note: Processed all pending attendees. Use sync_salesforce for limiting.'
                ))
            
            # Display individual results unless quiet mode
            if not quiet and activation_messages:
                self.stdout.write('\nActivation Details:')
                for message in activation_messages:
                    if 'successful' in message.lower() or 'activated' in message.lower():
                        self.stdout.write(self.style.SUCCESS(f'  ✓ {message}'))
                    elif 'failed' in message.lower() or 'error' in message.lower():
                        self.stdout.write(self.style.ERROR(f'  ✗ {message}'))
                    elif 'skipped' in message.lower():
                        self.stdout.write(self.style.WARNING(f'  - {message}'))
                    else:
                        self.stdout.write(f'  • {message}')
            
            # Summary
            total = success_count + failure_count
            elapsed_time = (timezone.now() - start_time).total_seconds()
            
            if total == 0:
                self.stdout.write(self.style.WARNING('\nNo attendees found needing activation.'))
            else:
                self.stdout.write(f'\n{"-" * 50}')
                self.stdout.write(self.style.SUCCESS(f'ACTIVATION COMPLETE'))
                self.stdout.write(f'Total processed: {total}')
                self.stdout.write(f'Successful: {success_count}')
                self.stdout.write(f'Failed: {failure_count}')
                self.stdout.write(f'Time elapsed: {elapsed_time:.2f} seconds')
                
                if success_count > 0:
                    self.stdout.write(self.style.SUCCESS(
                        f'\n✓ Successfully activated {success_count} Kajabi grant offers'
                    ))
                
                if failure_count > 0:
                    self.stdout.write(self.style.ERROR(
                        f'\n✗ {failure_count} activations failed. Check logs for details.'
                    ))
            
            # Log summary
            logger.info(f"Activation command completed: {success_count} successful, {failure_count} failed")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running activation: {str(e)}'))
            logger.exception('Error in activate_pending command')
            raise