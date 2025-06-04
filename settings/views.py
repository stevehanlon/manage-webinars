from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import ZoomSettings, SalesforceSettings, MS365Settings
from .forms import ZoomSettingsForm, SalesforceSettingsForm, MS365SettingsForm, EmailTestForm


@login_required
def settings_dashboard(request):
    """Main settings dashboard showing all configuration options."""
    zoom_settings = ZoomSettings.get_settings()
    zoom_configured = bool(zoom_settings.client_id and zoom_settings.client_secret and zoom_settings.account_id)
    
    salesforce_settings = SalesforceSettings.get_settings()
    salesforce_configured = bool(salesforce_settings.subdomain and salesforce_settings.username and 
                                salesforce_settings.password and salesforce_settings.security_token)
    
    ms365_settings = MS365Settings.get_settings()
    ms365_configured = bool(ms365_settings.client_id and ms365_settings.client_secret and 
                            ms365_settings.tenant_id and ms365_settings.owner_email)
    
    return render(request, 'settings/dashboard.html', {
        'zoom_configured': zoom_configured,
        'zoom_settings': zoom_settings,
        'salesforce_configured': salesforce_configured,
        'salesforce_settings': salesforce_settings,
        'ms365_configured': ms365_configured,
        'ms365_settings': ms365_settings
    })


@login_required
def zoom_settings_view(request):
    """View and update Zoom configuration settings."""
    zoom_settings = ZoomSettings.get_settings()
    
    if request.method == 'POST':
        form = ZoomSettingsForm(request.POST, instance=zoom_settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zoom settings updated successfully.')
            return redirect('zoom_settings')
    else:
        form = ZoomSettingsForm(instance=zoom_settings)
    
    return render(request, 'settings/zoom_settings.html', {
        'form': form,
        'zoom_settings': zoom_settings
    })


@login_required
def test_zoom_connection(request):
    """Test Zoom API connection and return JSON response."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        from webinars.zoom_service import ZoomService
        zoom_service = ZoomService()
        result = zoom_service.test_connection()
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        })


@login_required
def salesforce_settings_view(request):
    """View and update Salesforce configuration settings."""
    salesforce_settings = SalesforceSettings.get_settings()
    
    if request.method == 'POST':
        form = SalesforceSettingsForm(request.POST, instance=salesforce_settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salesforce settings updated successfully.')
            return redirect('salesforce_settings')
    else:
        form = SalesforceSettingsForm(instance=salesforce_settings)
    
    return render(request, 'settings/salesforce_settings.html', {
        'form': form,
        'salesforce_settings': salesforce_settings
    })


@login_required
def ms365_settings_view(request):
    """View and update MS365 configuration settings."""
    ms365_settings = MS365Settings.get_settings()
    
    if request.method == 'POST':
        form = MS365SettingsForm(request.POST, instance=ms365_settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'MS365 settings updated successfully.')
            return redirect('ms365_settings')
    else:
        form = MS365SettingsForm(instance=ms365_settings)
    
    return render(request, 'settings/ms365_settings.html', {
        'form': form,
        'ms365_settings': ms365_settings
    })


@login_required
def email_test_view(request):
    """Email test page for testing email delivery."""
    if request.method == 'POST':
        form = EmailTestForm(request.POST)
        if form.is_valid():
            test_email = form.cleaned_data['email']
            custom_message = form.cleaned_data.get('message', '').strip()
            
            # Use custom message or default
            if custom_message:
                message = custom_message
            else:
                message = """Hello World!

This is a test email from the Kajabi Webinar Manager system.

If you're receiving this email, it means:
✓ Email delivery is working correctly
✓ Your email configuration is properly set up
✓ The enhanced email service is functioning

System Information:
- Sent via enhanced email service with MS365 Graph API support
- Automatic fallback to SMTP if MS365 is unavailable
- Test initiated by: {user}
- Test time: {timestamp}

Have a great day!

---
Kajabi Webinar Manager
""".format(
                user=request.user.username,
                timestamp=timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')
            )
            
            try:
                # Import the enhanced email service
                from webinars.email_service import send_notification_email
                
                # Send the test email
                send_notification_email(
                    to_email=test_email,
                    subject="Test Email from Kajabi Webinar Manager",
                    message=message
                )
                
                messages.success(
                    request, 
                    f'Test email sent successfully to {test_email}! Check your inbox (and spam folder).'
                )
                
            except Exception as e:
                messages.error(
                    request,
                    f'Failed to send test email to {test_email}: {str(e)}'
                )
            
            return redirect('email_test')
    else:
        form = EmailTestForm()
    
    return render(request, 'settings/email_test.html', {
        'form': form
    })
