from django import forms
from .models import Webinar, WebinarDate, Attendee, WebinarBundle, BundleDate, BundleAttendee


class WebinarForm(forms.ModelForm):
    class Meta:
        model = Webinar
        fields = ['name', 'aliases', 'kajabi_grant_activation_hook_url', 'form_date_field', 
                 'checkout_date_field', 'error_notification_email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'aliases': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Enter alternative names (one per line)'
            }),
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
            'zoom_meeting_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Zoom meeting ID (numbers only)'
            }),
        }
    
    def clean_zoom_meeting_id(self):
        """Strip spaces from Zoom meeting ID."""
        zoom_id = self.cleaned_data.get('zoom_meeting_id', '')
        if zoom_id:
            # Remove all spaces and non-digit characters
            zoom_id = ''.join(filter(str.isdigit, zoom_id))
        return zoom_id if zoom_id else None


class AttendeeForm(forms.ModelForm):
    class Meta:
        model = Attendee
        fields = ['first_name', 'last_name', 'email', 'organization']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
        }


class WebinarBundleForm(forms.ModelForm):
    class Meta:
        model = WebinarBundle
        fields = ['name', 'aliases', 'kajabi_grant_activation_hook_url', 'form_date_field', 
                 'checkout_date_field', 'error_notification_email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'aliases': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Enter alternative names (one per line)'
            }),
            'kajabi_grant_activation_hook_url': forms.URLInput(attrs={'class': 'form-control'}),
            'form_date_field': forms.TextInput(attrs={'class': 'form-control'}),
            'checkout_date_field': forms.TextInput(attrs={'class': 'form-control'}),
            'error_notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class BundleDateForm(forms.ModelForm):
    webinar_dates = forms.ModelMultipleChoiceField(
        queryset=WebinarDate.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text="Select webinars to include in this bundle"
    )
    
    class Meta:
        model = BundleDate
        fields = ['date', 'webinar_dates']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # If editing, show webinars from the selected date
            webinars = self.instance.get_webinars_on_date()
            self.fields['webinar_dates'].queryset = webinars
            self.fields['webinar_dates'].initial = self.instance.webinar_dates.all()
        elif self.data.get('date'):
            # If date is submitted, filter webinars for that date
            from datetime import datetime
            try:
                date_str = self.data.get('date')
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                self.fields['webinar_dates'].queryset = WebinarDate.objects.filter(
                    date_time__date=selected_date,
                    deleted_at=None
                ).order_by('date_time', 'webinar__name')
            except:
                pass


class BundleAttendeeForm(forms.ModelForm):
    class Meta:
        model = BundleAttendee
        fields = ['first_name', 'last_name', 'email', 'organization']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
        }