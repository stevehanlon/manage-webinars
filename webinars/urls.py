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
    
    # Webinar URLs
    path('webinars/', views.WebinarListView.as_view(), name='webinar_list'),
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
    
    # API Webhooks
    path('api/attendee-webhook/', views.attendee_webhook, name='attendee_webhook'),
    
    # REST API
    path('', include(router.urls)),
]