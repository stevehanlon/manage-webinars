from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import ZoomSettings
from .forms import ZoomSettingsForm


@login_required
def settings_dashboard(request):
    """Main settings dashboard showing all configuration options."""
    zoom_settings = ZoomSettings.get_settings()
    zoom_configured = bool(zoom_settings.client_id and zoom_settings.client_secret and zoom_settings.account_id)
    
    return render(request, 'settings/dashboard.html', {
        'zoom_configured': zoom_configured,
        'zoom_settings': zoom_settings
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
