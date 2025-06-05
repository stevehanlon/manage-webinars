from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api

# REST API Router
router = DefaultRouter()
router.register(r'api/webinars', api.WebinarViewSet)
router.register(r'api/webinar-dates', api.WebinarDateViewSet)
router.register(r'api/attendees', api.AttendeeViewSet)

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('forthcoming/', views.forthcoming_webinars, name='forthcoming_webinars'),
    
    # Webinar URLs
    path('webinars/add/', views.WebinarCreateView.as_view(), name='webinar_create'),
    path('webinars/<int:pk>/', views.WebinarDetailView.as_view(), name='webinar_detail'),
    path('webinars/<int:pk>/edit/', views.WebinarUpdateView.as_view(), name='webinar_update'),
    path('webinars/<int:pk>/delete/', views.webinar_delete, name='webinar_delete'),
    
    # WebinarDate URLs
    path('webinars/<int:webinar_id>/dates/add/', views.WebinarDateCreateView.as_view(), name='webinar_date_create'),
    path('webinar-dates/<int:pk>/', views.WebinarDateDetailView.as_view(), name='webinar_date_detail'),
    path('webinar-dates/<int:pk>/edit/', views.WebinarDateUpdateView.as_view(), name='webinar_date_update'),
    path('webinar-dates/<int:pk>/delete/', views.webinar_date_delete, name='webinar_date_delete'),
    path('webinar-dates/<int:pk>/create-zoom/', views.create_zoom_webinar, name='create_zoom_webinar'),
    
    # Attendee URLs
    path('webinar-dates/<int:webinar_date_id>/attendees/add/', views.AttendeeCreateView.as_view(), name='attendee_create'),
    
    # Bundle URLs
    path('bundles/', views.BundleListView.as_view(), name='bundle_list'),
    path('bundles/add/', views.BundleCreateView.as_view(), name='bundle_create'),
    path('bundles/<int:pk>/', views.BundleDetailView.as_view(), name='bundle_detail'),
    path('bundles/<int:pk>/edit/', views.BundleUpdateView.as_view(), name='bundle_update'),
    path('bundles/<int:pk>/delete/', views.bundle_delete, name='bundle_delete'),
    
    # Bundle Date URLs
    path('bundles/<int:bundle_id>/dates/add/', views.BundleDateCreateView.as_view(), name='bundle_date_create'),
    path('bundle-dates/<int:pk>/', views.BundleDateDetailView.as_view(), name='bundle_date_detail'),
    path('bundle-dates/<int:pk>/edit/', views.BundleDateUpdateView.as_view(), name='bundle_date_update'),
    path('bundle-dates/<int:pk>/delete/', views.bundle_date_delete, name='bundle_date_delete'),
    
    # Bundle Attendee URLs
    path('bundle-dates/<int:bundle_date_id>/attendees/add/', views.BundleAttendeeCreateView.as_view(), name='bundle_attendee_create'),
    
    # API Webhooks
    path('api/attendee-webhook/', views.attendee_webhook, name='attendee_webhook'),
    
    # Activation URLs
    path('activate/attendee/<int:attendee_id>/', views.activate_attendee_view, name='activate_attendee'),
    path('activate/webinar-date/<int:webinar_date_id>/', views.activate_webinar_date_view, name='activate_webinar_date'),
    path('activate/bundle-date/<int:bundle_date_id>/', views.activate_bundle_date_view, name='activate_bundle_date'),
    path('api/cron/activate-pending/', views.cron_activate_pending, name='cron_activate_pending'),
    
    # Calendar Invite URLs
    path('send-calendar-invite/<int:webinar_date_id>/', views.send_calendar_invite_view, name='send_calendar_invite'),
    
    # Webhook Log URLs
    path('webhook-logs/', views.webhook_log_list, name='webhook_log_list'),
    path('webhook-logs/<int:pk>/', views.webhook_log_detail, name='webhook_log_detail'),
    path('webhook-logs/<int:pk>/delete/', views.webhook_log_delete, name='webhook_log_delete'),
    path('webhook-logs/clear-all/', views.webhook_log_clear_all, name='webhook_log_clear_all'),
    
    # Zoom Registration URLs
    path('attendees/<int:attendee_id>/register-zoom/', views.register_attendee_zoom, name='register_attendee_zoom'),
    
    # Salesforce Sync URLs
    path('attendees/<int:attendee_id>/sync-salesforce/', views.sync_attendee_salesforce, name='sync_attendee_salesforce'),
    
    # REST API
    path('', include(router.urls)),
]