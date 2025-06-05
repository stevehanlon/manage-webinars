from django.db import models
from django.urls import reverse
from django.utils import timezone


class BaseModel(models.Model):
    """Base model with common fields for all models."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Mark object as deleted instead of actual deletion."""
        self.deleted_at = timezone.now()
        self.save()
    
    @property
    def is_deleted(self):
        """Check if object is marked as deleted."""
        return self.deleted_at is not None


class Webinar(BaseModel):
    """Model representing a webinar series."""
    name = models.CharField(max_length=255)
    aliases = models.TextField(
        blank=True,
        help_text="Alternative names for this webinar (one per line). Used to match Kajabi offers/forms with different names."
    )
    kajabi_grant_activation_hook_url = models.URLField(max_length=500)
    form_date_field = models.CharField(max_length=255, default="Webinar options", 
                                      help_text="Field name in Kajabi form for date selection")
    checkout_date_field = models.CharField(max_length=255, default="custom_field_getting_started_with_wordpress_dates", 
                                         help_text="Field name in Kajabi checkout for date selection")
    error_notification_email = models.EmailField(default="info@awesometechtraining.com", 
                                               help_text="Email to notify on webhook processing errors")
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('webinar_detail', args=[self.id])
    
    def active_dates(self):
        """Return all active (non-deleted) webinar dates."""
        return self.webinardate_set.filter(deleted_at=None)
    
    def get_all_names(self):
        """Return a list of all names including the main name and aliases."""
        names = [self.name]
        if self.aliases:
            # Split aliases by newlines and add non-empty ones
            aliases = [alias.strip() for alias in self.aliases.split('\n') if alias.strip()]
            names.extend(aliases)
        return names


class WebinarDate(BaseModel):
    """Model representing a specific date for a webinar."""
    webinar = models.ForeignKey(Webinar, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    on_demand = models.BooleanField(default=False, help_text="Whether this is an on-demand webinar (no live date)")
    zoom_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    calendar_invite_sent_at = models.DateTimeField(null=True, blank=True, help_text="When calendar invites were sent to staff")
    calendar_invite_success = models.BooleanField(null=True, blank=True, help_text="Whether calendar invite sending was successful")
    calendar_invite_error = models.TextField(blank=True, help_text="Error message if calendar invite failed")
    
    def __str__(self):
        if self.on_demand:
            return f"{self.webinar.name} - On Demand"
        return f"{self.webinar.name} - {self.date_time.strftime('%Y-%m-%d %H:%M')}"
    
    def get_absolute_url(self):
        return reverse('webinar_date_detail', args=[self.id])
    
    def active_attendees(self):
        """Return all active (non-deleted) attendees."""
        return self.attendee_set.filter(deleted_at=None)
    
    def get_all_attendees(self):
        """Return all attendees including those from bundles."""
        from itertools import chain
        
        # Get direct attendees
        direct_attendees = list(self.active_attendees())
        
        # Get bundle attendees
        bundle_attendees = []
        for bundle_date in self.bundle_dates.filter(deleted_at=None):
            for attendee in bundle_date.active_attendees():
                # Add a flag to identify bundle attendees
                attendee.is_bundle_attendee = True
                attendee.bundle_name = bundle_date.bundle.name
                bundle_attendees.append(attendee)
        
        # Mark direct attendees
        for attendee in direct_attendees:
            attendee.is_bundle_attendee = False
            
        return list(chain(direct_attendees, bundle_attendees))
    
    @property
    def attendee_count(self):
        """Return the count of active attendees."""
        return self.active_attendees().count()
    
    @property
    def total_attendee_count(self):
        """Return the total count including bundle attendees."""
        bundle_count = sum(
            bundle_date.attendee_count 
            for bundle_date in self.bundle_dates.filter(deleted_at=None)
        )
        return self.attendee_count + bundle_count
    
    @property
    def has_attendees(self):
        """Check if this webinar date has any attendees."""
        return self.attendee_count > 0
    
    @property
    def calendar_invite_status(self):
        """Return a human-readable calendar invite status."""
        if not self.calendar_invite_sent_at:
            return "Not sent"
        elif self.calendar_invite_success:
            return "Sent"
        else:
            return "Failed"


class Attendee(BaseModel):
    """Model representing an attendee for a specific webinar date."""
    webinar_date = models.ForeignKey(WebinarDate, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    organization = models.CharField(max_length=255, blank=True, help_text="Organization name")
    activation_sent_at = models.DateTimeField(null=True, blank=True, help_text="When the Kajabi grant offer activation was sent")
    activation_success = models.BooleanField(null=True, blank=True, help_text="Whether the activation was successful")
    activation_error = models.TextField(blank=True, help_text="Error message if activation failed")
    zoom_registrant_id = models.CharField(max_length=100, blank=True, help_text="Zoom registrant ID if registered")
    zoom_join_url = models.URLField(max_length=500, blank=True, help_text="Personal Zoom join URL for this attendee")
    zoom_invite_link = models.URLField(max_length=500, blank=True, help_text="Meeting invite link for this attendee")
    zoom_registered_at = models.DateTimeField(null=True, blank=True, help_text="When registered in Zoom")
    zoom_registration_error = models.TextField(blank=True, help_text="Error message if Zoom registration failed")
    
    # Salesforce integration fields
    salesforce_contact_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Contact ID")
    salesforce_account_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Account ID")
    salesforce_task_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Task ID")
    salesforce_sync_error = models.TextField(blank=True, help_text="Error message if Salesforce sync failed")
    salesforce_synced_at = models.DateTimeField(null=True, blank=True, help_text="When successfully synced to Salesforce")
    salesforce_sync_pending = models.BooleanField(default=True, help_text="Whether this attendee needs to be synced to Salesforce")
    
    class Meta:
        unique_together = ['webinar_date', 'email']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"
    
    @property
    def zoom_registration_status(self):
        """Return a human-readable Zoom registration status."""
        if not self.webinar_date.zoom_meeting_id:
            return "No Zoom webinar"
        elif self.zoom_registrant_id:
            return "Registered"
        elif self.zoom_registration_error:
            return "Failed"
        else:
            return "Not registered"
    
    @property
    def can_register_zoom(self):
        """Return True if attendee can be registered in Zoom (has meeting ID but not registered)."""
        return (
            self.webinar_date.zoom_meeting_id and 
            not self.webinar_date.on_demand and 
            not self.zoom_registrant_id and 
            not self.is_deleted
        )
    
    @property
    def needs_activation(self):
        """Check if this attendee needs activation (webinar ended 2+ hours ago or is on-demand)."""
        if self.activation_sent_at:
            return False
        
        # On-demand webinars should be activated immediately
        if self.webinar_date.on_demand:
            return True
            
        if not self.webinar_date.date_time:
            return False
        
        # Check if webinar ended 2+ hours ago
        webinar_end_time = self.webinar_date.date_time + timezone.timedelta(hours=2)
        return timezone.now() >= webinar_end_time
    
    @property
    def activation_status(self):
        """Return a human-readable activation status."""
        if not self.activation_sent_at:
            if self.needs_activation:
                return "Pending"
            else:
                return "Not due"
        elif self.activation_success:
            return "Sent"
        else:
            return "Failed"
    
    @property
    def salesforce_status(self):
        """Return a human-readable Salesforce sync status."""
        if self.salesforce_synced_at:
            return "Synced"
        elif self.salesforce_sync_error:
            return "Failed"
        elif self.salesforce_sync_pending:
            return "Pending"
        else:
            return "Not scheduled"
    
    @property
    def salesforce_contact_url(self):
        """Return the Salesforce contact URL if synced."""
        if self.salesforce_contact_id:
            from settings.models import SalesforceSettings
            try:
                sf_settings = SalesforceSettings.objects.first()
                if sf_settings and sf_settings.subdomain:
                    return f"https://{sf_settings.subdomain}.my.salesforce.com/{self.salesforce_contact_id}"
            except:
                pass
        return None


class WebinarBundle(BaseModel):
    """Model representing a bundle of webinars that run on the same date."""
    name = models.CharField(max_length=255)
    aliases = models.TextField(
        blank=True,
        help_text="Alternative names for this bundle (one per line). Used to match Kajabi offers/forms with different names."
    )
    kajabi_grant_activation_hook_url = models.URLField(max_length=500)
    form_date_field = models.CharField(max_length=255, default="Bundle options", 
                                      help_text="Field name in Kajabi form for date selection")
    checkout_date_field = models.CharField(max_length=255, default="custom_field_bundle_dates", 
                                         help_text="Field name in Kajabi checkout for date selection")
    error_notification_email = models.EmailField(default="info@awesometechtraining.com", 
                                               help_text="Email to notify on webhook processing errors")
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('bundle_detail', args=[self.id])
    
    def active_dates(self):
        """Return all active (non-deleted) bundle dates."""
        return self.bundledate_set.filter(deleted_at=None)
    
    def get_all_names(self):
        """Return a list of all names including the main name and aliases."""
        names = [self.name]
        if self.aliases:
            # Split aliases by newlines and add non-empty ones
            aliases = [alias.strip() for alias in self.aliases.split('\n') if alias.strip()]
            names.extend(aliases)
        return names


class BundleDate(BaseModel):
    """Model representing a specific date for a bundle with multiple webinars."""
    bundle = models.ForeignKey(WebinarBundle, on_delete=models.CASCADE)
    date = models.DateField()
    webinar_dates = models.ManyToManyField(WebinarDate, related_name='bundle_dates')
    
    def __str__(self):
        return f"{self.bundle.name} - {self.date.strftime('%Y-%m-%d')}"
    
    def get_absolute_url(self):
        return reverse('bundle_date_detail', args=[self.id])
    
    def active_attendees(self):
        """Return all active (non-deleted) bundle attendees."""
        return self.bundleattendee_set.filter(deleted_at=None)
    
    @property
    def attendee_count(self):
        """Return the count of active attendees."""
        return self.active_attendees().count()
    
    @property
    def has_attendees(self):
        """Check if this bundle date has any attendees."""
        return self.attendee_count > 0
    
    def get_webinars_on_date(self):
        """Get all webinar dates on this bundle's date."""
        from datetime import datetime, time
        # Get start and end of the day
        start_datetime = datetime.combine(self.date, time.min)
        end_datetime = datetime.combine(self.date, time.max)
        
        # Make timezone aware if needed
        from django.utils import timezone
        if timezone.is_aware(WebinarDate.objects.first().date_time if WebinarDate.objects.exists() else timezone.now()):
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        
        return WebinarDate.objects.filter(
            date_time__date=self.date,
            deleted_at=None
        ).order_by('date_time', 'webinar__name')


class BundleAttendee(BaseModel):
    """Model representing an attendee for a specific bundle date."""
    bundle_date = models.ForeignKey(BundleDate, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    organization = models.CharField(max_length=255, blank=True, help_text="Organization name")
    activation_sent_at = models.DateTimeField(null=True, blank=True, help_text="When the Kajabi grant offer activation was sent")
    activation_success = models.BooleanField(null=True, blank=True, help_text="Whether the activation was successful")
    activation_error = models.TextField(blank=True, help_text="Error message if activation failed")
    
    # Salesforce integration fields
    salesforce_contact_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Contact ID")
    salesforce_account_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Account ID")
    salesforce_task_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Task ID")
    salesforce_sync_error = models.TextField(blank=True, help_text="Error message if Salesforce sync failed")
    salesforce_synced_at = models.DateTimeField(null=True, blank=True, help_text="When successfully synced to Salesforce")
    salesforce_sync_pending = models.BooleanField(default=True, help_text="Whether this attendee needs to be synced to Salesforce")
    
    class Meta:
        unique_together = ['bundle_date', 'email']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email} (Bundle)"
    
    @property
    def needs_activation(self):
        """Check if this attendee needs activation (latest webinar ended 2+ hours ago)."""
        if self.activation_sent_at:
            return False
        
        # Get the latest webinar end time for this bundle date
        webinars_on_date = self.bundle_date.get_webinars_on_date()
        if not webinars_on_date.exists():
            return False
        
        # Find the latest webinar time and add 2 hours
        latest_webinar = webinars_on_date.order_by('-date_time').first()
        webinar_end_time = latest_webinar.date_time + timezone.timedelta(hours=2)
        return timezone.now() >= webinar_end_time
    
    @property
    def activation_status(self):
        """Return a human-readable activation status."""
        if not self.activation_sent_at:
            if self.needs_activation:
                return "Pending"
            else:
                return "Not due"
        elif self.activation_success:
            return "Sent"
        else:
            return "Failed"
    
    @property
    def salesforce_status(self):
        """Return a human-readable Salesforce sync status."""
        if self.salesforce_synced_at:
            return "Synced"
        elif self.salesforce_sync_error:
            return "Failed"
        elif self.salesforce_sync_pending:
            return "Pending"
        else:
            return "Not scheduled"
    
    @property
    def salesforce_contact_url(self):
        """Return the Salesforce contact URL if synced."""
        if self.salesforce_contact_id:
            from settings.models import SalesforceSettings
            try:
                sf_settings = SalesforceSettings.objects.first()
                if sf_settings and sf_settings.subdomain:
                    return f"https://{sf_settings.subdomain}.my.salesforce.com/{self.salesforce_contact_id}"
            except:
                pass
        return None


class OnDemandAttendee(BaseModel):
    """Model representing an attendee who has on-demand access to webinar recordings."""
    webinar = models.ForeignKey(Webinar, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    organization = models.CharField(max_length=255, blank=True, help_text="Organization name")
    activation_sent_at = models.DateTimeField(null=True, blank=True, help_text="When the Kajabi grant offer activation was sent")
    activation_success = models.BooleanField(null=True, blank=True, help_text="Whether the activation was successful")
    activation_error = models.TextField(blank=True, help_text="Error message if activation failed")
    
    # Salesforce integration fields
    salesforce_contact_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Contact ID")
    salesforce_account_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Account ID")
    salesforce_task_id = models.CharField(max_length=50, blank=True, help_text="Salesforce Task ID")
    salesforce_sync_error = models.TextField(blank=True, help_text="Error message if Salesforce sync failed")
    salesforce_synced_at = models.DateTimeField(null=True, blank=True, help_text="When successfully synced to Salesforce")
    salesforce_sync_pending = models.BooleanField(default=True, help_text="Whether this attendee needs to be synced to Salesforce")
    
    class Meta:
        unique_together = ['webinar', 'email']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email} (On-Demand)"
    
    @property
    def needs_activation(self):
        """On-demand attendees should be activated immediately."""
        return not self.activation_sent_at
    
    @property
    def activation_status(self):
        """Return a human-readable activation status."""
        if not self.activation_sent_at:
            return "Pending"
        elif self.activation_success:
            return "Sent"
        else:
            return "Failed"
    
    @property
    def salesforce_status(self):
        """Return a human-readable Salesforce sync status."""
        if self.salesforce_synced_at:
            return "Synced"
        elif self.salesforce_sync_error:
            return "Failed"
        elif self.salesforce_sync_pending:
            return "Pending"
        else:
            return "Not scheduled"
    
    @property
    def salesforce_contact_url(self):
        """Return the Salesforce contact URL if synced."""
        if self.salesforce_contact_id:
            from settings.models import SalesforceSettings
            try:
                sf_settings = SalesforceSettings.objects.first()
                if sf_settings and sf_settings.subdomain:
                    return f"https://{sf_settings.subdomain}.my.salesforce.com/{self.salesforce_contact_id}"
            except:
                pass
        return None


class WebhookLog(models.Model):
    """Model to store webhook request logs for debugging."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=200)
    headers = models.JSONField()
    body = models.TextField(blank=True)
    response_status = models.IntegerField()
    response_body = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.path} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def body_preview(self):
        """Return first 100 characters of body for preview."""
        if self.body:
            return self.body[:100] + ('...' if len(self.body) > 100 else '')
        return ''
    
    @property
    def formatted_body(self):
        """Return formatted JSON body if possible."""
        if self.body:
            try:
                import json
                data = json.loads(self.body)
                return json.dumps(data, indent=2)
            except:
                return self.body
        return ''