from django import forms
from .models import ZoomSettings, SalesforceSettings, MS365Settings


class ZoomSettingsForm(forms.ModelForm):
    client_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep current value'
        }),
        help_text="Zoom OAuth App Client Secret (leave blank to keep current value)",
        required=False
    )
    
    class Meta:
        model = ZoomSettings
        fields = ['client_id', 'client_secret', 'account_id', 'webinar_template_id']
        widgets = {
            'client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'account_id': forms.TextInput(attrs={'class': 'form-control'}),
            'webinar_template_id': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is an existing instance, make client_secret not required
        if self.instance and self.instance.pk:
            self.fields['client_secret'].required = False
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # If client_secret is empty and this is an update, preserve the existing value
        if not self.cleaned_data.get('client_secret') and self.instance.pk:
            # Get the current value from the database
            current_instance = ZoomSettings.objects.get(pk=self.instance.pk)
            instance.client_secret = current_instance.client_secret
        
        if commit:
            instance.save()
        return instance


class SalesforceSettingsForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep current value'
        }),
        help_text="Salesforce password (leave blank to keep current value)",
        required=False
    )
    security_token = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep current value'
        }),
        help_text="Salesforce security token (leave blank to keep current value)",
        required=False
    )
    
    class Meta:
        model = SalesforceSettings
        fields = ['subdomain', 'username', 'password', 'security_token']
        widgets = {
            'subdomain': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is an existing instance, make password fields not required
        if self.instance and self.instance.pk:
            self.fields['password'].required = False
            self.fields['security_token'].required = False
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # If password fields are empty and this is an update, preserve the existing values
        if self.instance.pk:
            current_instance = SalesforceSettings.objects.get(pk=self.instance.pk)
            
            if not self.cleaned_data.get('password'):
                instance.password = current_instance.password
            
            if not self.cleaned_data.get('security_token'):
                instance.security_token = current_instance.security_token
        
        if commit:
            instance.save()
        return instance


class MS365SettingsForm(forms.ModelForm):
    client_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep current value'
        }),
        help_text="Microsoft Azure App Client Secret (leave blank to keep current value)",
        required=False
    )
    
    class Meta:
        model = MS365Settings
        fields = ['client_id', 'client_secret', 'tenant_id', 'owner_email']
        widgets = {
            'client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'tenant_id': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is an existing instance, make client_secret not required
        if self.instance and self.instance.pk:
            self.fields['client_secret'].required = False
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # If client_secret is empty and this is an update, preserve the existing value
        if not self.cleaned_data.get('client_secret') and self.instance.pk:
            # Get the current value from the database
            current_instance = MS365Settings.objects.get(pk=self.instance.pk)
            instance.client_secret = current_instance.client_secret
        
        if commit:
            instance.save()
        return instance



class EmailTestForm(forms.Form):
    email = forms.EmailField(
        label="Test Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address to send test email'
        }),
        help_text="Enter the email address where you want to send a test email"
    )
    
    message = forms.CharField(
        label="Test Message (Optional)",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter a custom test message or leave blank for default'
        }),
        required=False,
        help_text="Optional custom message. If left blank, a standard test message will be sent."
    )
