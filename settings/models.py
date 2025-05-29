from django.db import models
from django.core.exceptions import ValidationError


class ZoomSettings(models.Model):
    """
    Singleton model for storing Zoom API configuration.
    Only one instance should exist.
    """
    client_id = models.CharField(
        max_length=255,
        help_text="Zoom OAuth App Client ID"
    )
    client_secret = models.CharField(
        max_length=255,
        help_text="Zoom OAuth App Client Secret"
    )
    account_id = models.CharField(
        max_length=255,
        help_text="Zoom Account ID"
    )
    webinar_template_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Default Zoom Webinar Template ID (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Zoom Settings"
        verbose_name_plural = "Zoom Settings"
    
    def __str__(self):
        return "Zoom Configuration"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and ZoomSettings.objects.exists():
            raise ValidationError("Only one Zoom configuration can exist.")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get the current Zoom settings instance, create if doesn't exist."""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'client_id': '',
                'client_secret': '',
                'account_id': '',
                'webinar_template_id': ''
            }
        )
        return settings
