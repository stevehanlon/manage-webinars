from django.urls import path
from . import views

urlpatterns = [
    path('', views.settings_dashboard, name='settings_dashboard'),
    path('zoom/', views.zoom_settings_view, name='zoom_settings'),
    path('zoom/test/', views.test_zoom_connection, name='test_zoom_connection'),
    path('salesforce/', views.salesforce_settings_view, name='salesforce_settings'),
]