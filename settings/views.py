from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import ZoomSettings, SalesforceSettings, MS365Settings
from .forms import ZoomSettingsForm, SalesforceSettingsForm, MS365SettingsForm


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
