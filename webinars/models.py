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


class WebinarDate(BaseModel):
    """Model representing a specific date for a webinar."""
    webinar = models.ForeignKey(Webinar, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    zoom_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
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


class Attendee(BaseModel):
    """Model representing an attendee for a specific webinar date."""
    webinar_date = models.ForeignKey(WebinarDate, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    
    class Meta:
        unique_together = ['webinar_date', 'email']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"


class WebinarBundle(BaseModel):
    """Model representing a bundle of webinars that run on the same date."""
    name = models.CharField(max_length=255)
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
    
    class Meta:
        unique_together = ['bundle_date', 'email']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email} (Bundle)"
