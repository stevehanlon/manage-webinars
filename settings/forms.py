from django import forms
from .models import ZoomSettings


class ZoomSettingsForm(forms.ModelForm):
    client_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Zoom OAuth App Client Secret"
    )
    
    class Meta:
        model = ZoomSettings
        fields = ['client_id', 'client_secret', 'account_id', 'webinar_template_id']
        widgets = {
            'client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'account_id': forms.TextInput(attrs={'class': 'form-control'}),
            'webinar_template_id': forms.TextInput(attrs={'class': 'form-control'}),
        }