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
    
    @property
    def attendee_count(self):
        """Return the count of active attendees."""
        return self.active_attendees().count()
    
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
