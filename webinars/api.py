from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone

from .models import Webinar, WebinarDate, Attendee


class WebinarViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Webinars
    """
    queryset = Webinar.objects.filter(deleted_at=None)
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_destroy(self, instance):
        # Soft delete instead of hard delete
        instance.deleted_at = timezone.now()
        instance.save()
    
    @action(detail=True, methods=['get'])
    def dates(self, request, pk=None):
        """Get all dates for a specific webinar"""
        webinar = self.get_object()
        dates = webinar.active_dates()
        
        result = []
        for date in dates:
            result.append({
                'id': date.id,
                'date_time': date.date_time,
                'zoom_meeting_id': date.zoom_meeting_id,
                'attendee_count': date.attendee_count,
                'created_at': date.created_at,
                'updated_at': date.updated_at
            })
        
        return Response(result)


class WebinarDateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for WebinarDates
    """
    queryset = WebinarDate.objects.filter(deleted_at=None)
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_destroy(self, instance):
        # Only allow deletion if there are no attendees
        if instance.has_attendees:
            return Response(
                {'error': 'Cannot delete a webinar date with attendees'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Soft delete instead of hard delete
        instance.deleted_at = timezone.now()
        instance.save()
    
    @action(detail=True, methods=['get'])
    def attendees(self, request, pk=None):
        """Get all attendees for a specific webinar date"""
        webinar_date = self.get_object()
        attendees = webinar_date.active_attendees()
        
        result = []
        for attendee in attendees:
            result.append({
                'id': attendee.id,
                'first_name': attendee.first_name,
                'last_name': attendee.last_name,
                'email': attendee.email,
                'organization': attendee.organization,
                'created_at': attendee.created_at,
                'updated_at': attendee.updated_at
            })
        
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def create_zoom(self, request, pk=None):
        """Create a Zoom webinar for this date"""
        webinar_date = self.get_object()
        
        # Placeholder for future Zoom integration
        # This will be implemented later
        webinar_date.zoom_meeting_id = "placeholder_zoom_id"
        webinar_date.save()
        
        return Response({'status': 'Zoom webinar creation initiated (placeholder)'})


class AttendeeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Attendees
    """
    queryset = Attendee.objects.filter(deleted_at=None)
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_destroy(self, instance):
        # Soft delete instead of hard delete
        instance.deleted_at = timezone.now()
        instance.save()