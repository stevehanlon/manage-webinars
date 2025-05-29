from rest_framework import serializers
from .models import Webinar, WebinarDate, Attendee


class WebinarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webinar
        fields = ['id', 'name', 'kajabi_grant_activation_hook_url', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class WebinarDateSerializer(serializers.ModelSerializer):
    attendee_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = WebinarDate
        fields = ['id', 'webinar', 'date_time', 'zoom_meeting_id', 'attendee_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class AttendeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendee
        fields = ['id', 'webinar_date', 'first_name', 'last_name', 'email', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']