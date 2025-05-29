from django.contrib import admin
from .models import ZoomSettings, SalesforceSettings


@admin.register(ZoomSettings)
class ZoomSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'account_id', 'webinar_template_id', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not ZoomSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of the settings
        return False


@admin.register(SalesforceSettings)
class SalesforceSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'subdomain', 'username', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SalesforceSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of the settings
        return False
