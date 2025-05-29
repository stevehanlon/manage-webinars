from django import forms
from .models import Webinar, WebinarDate, Attendee


class WebinarForm(forms.ModelForm):
    class Meta:
        model = Webinar
        fields = ['name', 'kajabi_grant_activation_hook_url', 'form_date_field', 
                 'checkout_date_field', 'error_notification_email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'kajabi_grant_activation_hook_url': forms.URLInput(attrs={'class': 'form-control'}),
            'form_date_field': forms.TextInput(attrs={'class': 'form-control'}),
            'checkout_date_field': forms.TextInput(attrs={'class': 'form-control'}),
            'error_notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class WebinarDateForm(forms.ModelForm):
    class Meta:
        model = WebinarDate
        fields = ['date_time', 'zoom_meeting_id']
        widgets = {
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'zoom_meeting_id': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AttendeeForm(forms.ModelForm):
    class Meta:
        model = Attendee
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }