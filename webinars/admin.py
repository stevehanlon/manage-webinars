from django.contrib import admin
from .models import Webinar, WebinarDate, Attendee, WebinarBundle, BundleDate, BundleAttendee


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
    list_display = ['full_name', 'email', 'webinar_name', 'webinar_date', 'created_at', 'is_deleted']
    list_filter = ['webinar_date__webinar', 'webinar_date__date_time', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'webinar_date__webinar__name']
    
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