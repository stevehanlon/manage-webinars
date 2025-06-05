from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Webinar, WebinarDate, Attendee, WebinarBundle, BundleDate, BundleAttendee, WebhookLog


class WebinarDateInline(admin.TabularInline):
    model = WebinarDate
    extra = 0
    fields = ['date_time', 'zoom_meeting_id', 'attendee_count']
    readonly_fields = ['attendee_count']
    
    def attendee_count(self, obj):
        return obj.attendee_count if obj.id else 0
    
    attendee_count.short_description = 'Attendees'


@admin.register(Webinar)
class WebinarAdmin(admin.ModelAdmin):
    list_display = ['name', 'date_count', 'created_at', 'updated_at', 'is_deleted']
    search_fields = ['name']
    list_filter = ['created_at', 'updated_at']
    inlines = [WebinarDateInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'aliases', 'kajabi_grant_activation_hook_url')
        }),
        ('Webhook Configuration', {
            'fields': ('form_date_field', 'checkout_date_field', 'error_notification_email'),
            'classes': ('collapse',),
            'description': 'Configure Kajabi webhook field mappings'
        }),
    )
    
    def date_count(self, obj):
        return obj.active_dates().count()
    
    date_count.short_description = 'Dates'
    
    def is_deleted(self, obj):
        return obj.is_deleted
    
    is_deleted.boolean = True
    is_deleted.short_description = 'Deleted'


class AttendeeInline(admin.TabularInline):
    model = Attendee
    extra = 0
    fields = ['first_name', 'last_name', 'email']


@admin.register(WebinarDate)
class WebinarDateAdmin(admin.ModelAdmin):
    list_display = ['webinar', 'date_time', 'zoom_meeting_id', 'attendee_count', 'created_at', 'is_deleted']
    list_filter = ['webinar', 'date_time', 'created_at']
    search_fields = ['webinar__name', 'zoom_meeting_id']
    inlines = [AttendeeInline]
    
    def is_deleted(self, obj):
        return obj.is_deleted
    
    is_deleted.boolean = True
    is_deleted.short_description = 'Deleted'


@admin.register(Attendee)
class AttendeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'webinar_name', 'webinar_date', 'zoom_status_display', 'zoom_actions', 'created_at', 'is_deleted']
    list_filter = ['webinar_date__webinar', 'webinar_date__date_time', 'created_at', 'zoom_registrant_id']
    search_fields = ['first_name', 'last_name', 'email', 'webinar_date__webinar__name', 'zoom_registrant_id']
    
    class Media:
        js = ('js/attendee_admin.js',)
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    full_name.short_description = 'Name'
    
    def webinar_name(self, obj):
        return obj.webinar_date.webinar.name
    
    webinar_name.short_description = 'Webinar'
    
    def webinar_date(self, obj):
        return obj.webinar_date.date_time.strftime('%Y-%m-%d %H:%M')
    
    webinar_date.short_description = 'Date'
    
    def is_deleted(self, obj):
        return obj.is_deleted
    
    is_deleted.boolean = True
    is_deleted.short_description = 'Deleted'
    
    def zoom_status_display(self, obj):
        status = obj.zoom_registration_status
        if status == "Registered":
            return format_html('<span style="color: green;">✓ {}</span>', status)
        elif status == "Failed":
            return format_html('<span style="color: red;">✗ {}</span>', status)
        elif status == "No Zoom webinar":
            return format_html('<span style="color: gray;">{}</span>', status)
        else:
            return format_html('<span style="color: orange;">{}</span>', status)
    
    zoom_status_display.short_description = 'Zoom Status'
    zoom_status_display.admin_order_field = 'zoom_registrant_id'
    
    def zoom_actions(self, obj):
        if obj.can_register_zoom:
            return format_html(
                '<button onclick="registerZoom({})" class="btn btn-sm btn-primary">Add to Zoom</button>',
                obj.id
            )
        elif obj.zoom_invite_link:
            return format_html(
                '<a href="{}" target="_blank" class="btn btn-sm btn-success">View Invite</a>',
                obj.zoom_invite_link
            )
        else:
            return "-"
    
    zoom_actions.short_description = 'Actions'
    zoom_actions.allow_tags = True

class BundleDateInline(admin.TabularInline):
    model = BundleDate
    extra = 0
    fields = ['date', 'webinar_count', 'attendee_count']
    readonly_fields = ['webinar_count', 'attendee_count']
    
    def webinar_count(self, obj):
        return obj.webinar_dates.count() if obj.id else 0
    
    webinar_count.short_description = 'Webinars'
    
    def attendee_count(self, obj):
        return obj.attendee_count if obj.id else 0
    
    attendee_count.short_description = 'Attendees'


@admin.register(WebinarBundle)
class WebinarBundleAdmin(admin.ModelAdmin):
    list_display = ['name', 'date_count', 'created_at', 'updated_at', 'is_deleted']
    search_fields = ['name']
    list_filter = ['created_at', 'updated_at']
    inlines = [BundleDateInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'aliases', 'kajabi_grant_activation_hook_url')
        }),
        ('Webhook Configuration', {
            'fields': ('form_date_field', 'checkout_date_field', 'error_notification_email'),
            'classes': ('collapse',),
            'description': 'Configure Kajabi webhook field mappings'
        }),
    )
    
    def date_count(self, obj):
        return obj.active_dates().count()
    
    date_count.short_description = 'Dates'
    
    def is_deleted(self, obj):
        return obj.is_deleted
    
    is_deleted.boolean = True
    is_deleted.short_description = 'Deleted'


class BundleAttendeeInline(admin.TabularInline):
    model = BundleAttendee
    extra = 0
    fields = ['first_name', 'last_name', 'email']


@admin.register(BundleDate)
class BundleDateAdmin(admin.ModelAdmin):
    list_display = ['bundle', 'date', 'webinar_count', 'attendee_count', 'created_at', 'is_deleted']
    list_filter = ['bundle', 'date', 'created_at']
    search_fields = ['bundle__name']
    inlines = [BundleAttendeeInline]
    filter_horizontal = ['webinar_dates']
    
    def webinar_count(self, obj):
        return obj.webinar_dates.count()
    
    webinar_count.short_description = 'Webinars'
    
    def is_deleted(self, obj):
        return obj.is_deleted
    
    is_deleted.boolean = True
    is_deleted.short_description = 'Deleted'


@admin.register(BundleAttendee)
class BundleAttendeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'bundle_name', 'bundle_date_display', 'created_at', 'is_deleted']
    list_filter = ['bundle_date__bundle', 'bundle_date__date', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'bundle_date__bundle__name']
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    full_name.short_description = 'Name'
    
    def bundle_name(self, obj):
        return obj.bundle_date.bundle.name
    
    bundle_name.short_description = 'Bundle'
    
    def bundle_date_display(self, obj):
        return obj.bundle_date.date.strftime('%Y-%m-%d')
    
    bundle_date_display.short_description = 'Date'
    
    def is_deleted(self, obj):
        return obj.is_deleted
    
    is_deleted.boolean = True
    is_deleted.short_description = 'Deleted'


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'method', 'path', 'status_icon', 'body_preview', 'response_status', 'processing_time_display']
    list_filter = ['success', 'method', 'created_at', 'response_status']
    search_fields = ['body', 'error_message', 'path']
    readonly_fields = ['created_at', 'method', 'path', 'headers', 'formatted_body_display', 
                      'response_status', 'formatted_response_display', 'success', 'error_message', 
                      'processing_time_ms']
    date_hierarchy = 'created_at'
    
    def status_icon(self, obj):
        if obj.success:
            return format_html('<span style="color: green; font-size: 20px;">✓</span>')
        else:
            return format_html('<span style="color: red; font-size: 20px;">✗</span>')
    
    status_icon.short_description = 'Status'
    status_icon.admin_order_field = 'success'
    
    def processing_time_display(self, obj):
        if obj.processing_time_ms:
            return f"{obj.processing_time_ms} ms"
        return "-"
    
    processing_time_display.short_description = 'Time'
    processing_time_display.admin_order_field = 'processing_time_ms'
    
    def formatted_body_display(self, obj):
        if obj.body:
            formatted = obj.formatted_body
            return format_html('<pre style="white-space: pre-wrap; word-wrap: break-word;">{}</pre>', formatted)
        return "-"
    
    formatted_body_display.short_description = 'Request Body'
    
    def formatted_response_display(self, obj):
        if obj.response_body:
            try:
                import json
                data = json.loads(obj.response_body)
                formatted = json.dumps(data, indent=2)
            except:
                formatted = obj.response_body
            return format_html('<pre style="white-space: pre-wrap; word-wrap: break-word;">{}</pre>', formatted)
        return "-"
    
    formatted_response_display.short_description = 'Response Body'
    
    def has_add_permission(self, request):
        # Disable manual creation of webhook logs
        return False
    
    def has_change_permission(self, request, obj=None):
        # Disable editing of webhook logs
        return False
    
    fieldsets = (
        ('Request Information', {
            'fields': ('created_at', 'method', 'path', 'headers', 'formatted_body_display')
        }),
        ('Response Information', {
            'fields': ('response_status', 'formatted_response_display', 'success', 'error_message')
        }),
        ('Performance', {
            'fields': ('processing_time_ms',)
        }),
    )