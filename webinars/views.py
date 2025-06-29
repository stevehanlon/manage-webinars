from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone

from .models import Webinar, WebinarDate, Attendee, WebinarBundle, BundleDate, BundleAttendee, Download, ClinicBooking
from .forms import WebinarForm, WebinarDateForm, AttendeeForm, WebinarBundleForm, BundleDateForm, BundleAttendeeForm


# Dashboard View
@login_required
def dashboard(request):
    webinars = Webinar.objects.filter(deleted_at=None)
    bundles = WebinarBundle.objects.filter(deleted_at=None)
    return render(request, 'webinars/dashboard.html', {
        'webinars': webinars,
        'bundles': bundles
    })


# Webinar Views
class WebinarDetailView(LoginRequiredMixin, DetailView):
    model = Webinar
    template_name = 'webinars/webinar_detail.html'
    context_object_name = 'webinar'
    
    def get_queryset(self):
        return Webinar.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all webinar dates (no need to filter out on-demand since we're not using them anymore)
        context['dates'] = self.object.active_dates().order_by('date_time')
        
        # Get on-demand attendees directly
        from .models import OnDemandAttendee
        on_demand_attendees = OnDemandAttendee.objects.filter(
            webinar=self.object,
            deleted_at=None
        ).order_by('-created_at')
        
        context['on_demand_attendees'] = on_demand_attendees
        context['on_demand_attendee_count'] = on_demand_attendees.count()
        
        return context


class WebinarCreateView(LoginRequiredMixin, CreateView):
    model = Webinar
    form_class = WebinarForm
    template_name = 'webinars/webinar_form.html'
    success_url = reverse_lazy('dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Webinar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Webinar created successfully.')
        return super().form_valid(form)


class WebinarUpdateView(LoginRequiredMixin, UpdateView):
    model = Webinar
    form_class = WebinarForm
    template_name = 'webinars/webinar_form.html'
    
    def get_queryset(self):
        return Webinar.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Webinar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Webinar updated successfully.')
        return super().form_valid(form)


@login_required
def webinar_delete(request, pk):
    webinar = get_object_or_404(Webinar, pk=pk, deleted_at=None)
    
    if request.method == 'POST':
        webinar.soft_delete()
        messages.success(request, 'Webinar deleted successfully.')
        return redirect('dashboard')
    
    return render(request, 'webinars/webinar_confirm_delete.html', {'webinar': webinar})


# WebinarDate Views
class WebinarDateDetailView(LoginRequiredMixin, DetailView):
    model = WebinarDate
    template_name = 'webinars/webinar_date_detail.html'
    context_object_name = 'webinar_date'
    
    def get_queryset(self):
        return WebinarDate.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attendees'] = self.object.get_all_attendees()
        return context


class WebinarDateCreateView(LoginRequiredMixin, CreateView):
    model = WebinarDate
    form_class = WebinarDateForm
    template_name = 'webinars/webinar_date_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        webinar = get_object_or_404(Webinar, pk=self.kwargs['webinar_id'], deleted_at=None)
        context['webinar'] = webinar
        context['title'] = f'Add New Date for {webinar.name}'
        return context
    
    def form_valid(self, form):
        webinar = get_object_or_404(Webinar, pk=self.kwargs['webinar_id'], deleted_at=None)
        form.instance.webinar = webinar
        messages.success(self.request, 'Webinar date created successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('webinar_detail', args=[self.kwargs['webinar_id']])


class WebinarDateUpdateView(LoginRequiredMixin, UpdateView):
    model = WebinarDate
    form_class = WebinarDateForm
    template_name = 'webinars/webinar_date_form.html'
    
    def get_queryset(self):
        return WebinarDate.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['webinar'] = self.object.webinar
        context['title'] = f'Edit {self.object.webinar.name}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Webinar date updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('webinar_detail', args=[self.object.webinar.id])


@login_required
def webinar_date_delete(request, pk):
    webinar_date = get_object_or_404(WebinarDate, pk=pk, deleted_at=None)
    webinar_id = webinar_date.webinar.id
    
    if webinar_date.has_attendees:
        messages.error(request, 'Cannot delete a webinar date with attendees.')
        return redirect('webinar_date_detail', pk=pk)
    
    if request.method == 'POST':
        webinar_date.soft_delete()
        messages.success(request, 'Webinar date deleted successfully.')
        return redirect('webinar_detail', pk=webinar_id)
    
    return render(request, 'webinars/webinar_date_confirm_delete.html', {'webinar_date': webinar_date})


@login_required
def create_zoom_webinar(request, pk):
    webinar_date = get_object_or_404(WebinarDate, pk=pk, deleted_at=None)
    
    # Check if Zoom meeting already exists
    if webinar_date.zoom_meeting_id:
        messages.warning(request, 'A Zoom meeting already exists for this webinar date.')
        return redirect('webinar_date_detail', pk=pk)
    
    try:
        from .zoom_service import ZoomService
        zoom_service = ZoomService()
        
        # Create the Zoom webinar
        webinar_data = zoom_service.create_webinar(webinar_date)
        
        # Save the webinar ID to the webinar date
        webinar_date.zoom_meeting_id = webinar_data['webinar_id']
        webinar_date.save()
        
        messages.success(
            request, 
            f'Zoom webinar created successfully! Webinar ID: {webinar_data["webinar_id"]}'
        )
        
    except Exception as e:
        messages.error(
            request, 
            f'Failed to create Zoom webinar: {str(e)}. Please check your Zoom settings.'
        )
    
    return redirect('webinar_date_detail', pk=pk)


# Attendee Add Views
class AttendeeCreateView(LoginRequiredMixin, CreateView):
    model = Attendee
    form_class = AttendeeForm
    template_name = 'webinars/attendee_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        webinar_date = get_object_or_404(WebinarDate, pk=self.kwargs['webinar_date_id'], deleted_at=None)
        context['webinar_date'] = webinar_date
        context['title'] = f'Add Attendee to {webinar_date.webinar.name}'
        context['is_bundle'] = False
        return context
    
    def form_valid(self, form):
        webinar_date = get_object_or_404(WebinarDate, pk=self.kwargs['webinar_date_id'], deleted_at=None)
        form.instance.webinar_date = webinar_date
        
        # Check if attendee already exists
        existing = Attendee.objects.filter(
            webinar_date=webinar_date,
            email=form.cleaned_data['email']
        ).first()
        
        if existing:
            if existing.is_deleted:
                # Restore deleted attendee
                existing.deleted_at = None
                existing.first_name = form.cleaned_data['first_name']
                existing.last_name = form.cleaned_data['last_name']
                existing.save()
                messages.success(self.request, 'Attendee restored successfully.')
            else:
                messages.warning(self.request, 'An attendee with this email already exists for this webinar.')
            return redirect('webinar_date_detail', pk=webinar_date.id)
        
        messages.success(self.request, 'Attendee added successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('webinar_date_detail', args=[self.kwargs['webinar_date_id']])


class BundleAttendeeCreateView(LoginRequiredMixin, CreateView):
    model = BundleAttendee
    form_class = BundleAttendeeForm
    template_name = 'webinars/attendee_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bundle_date = get_object_or_404(BundleDate, pk=self.kwargs['bundle_date_id'], deleted_at=None)
        context['bundle_date'] = bundle_date
        context['title'] = f'Add Attendee to {bundle_date.bundle.name}'
        context['is_bundle'] = True
        return context
    
    def form_valid(self, form):
        bundle_date = get_object_or_404(BundleDate, pk=self.kwargs['bundle_date_id'], deleted_at=None)
        form.instance.bundle_date = bundle_date
        
        # Check if attendee already exists
        existing = BundleAttendee.objects.filter(
            bundle_date=bundle_date,
            email=form.cleaned_data['email']
        ).first()
        
        if existing:
            if existing.is_deleted:
                # Restore deleted attendee
                existing.deleted_at = None
                existing.first_name = form.cleaned_data['first_name']
                existing.last_name = form.cleaned_data['last_name']
                existing.save()
                messages.success(self.request, 'Bundle attendee restored successfully.')
            else:
                messages.warning(self.request, 'An attendee with this email already exists for this bundle.')
            return redirect('bundle_date_detail', pk=bundle_date.id)
        
        messages.success(self.request, 'Bundle attendee added successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('bundle_date_detail', args=[self.kwargs['bundle_date_id']])


# Attendee Views
@csrf_exempt
def attendee_webhook(request):
    """Webhook endpoint for registering attendees from Kajabi."""
    import logging
    import time
    from .models import WebhookLog
    
    logger = logging.getLogger('webinars')
    start_time = time.time()
    
    # Log all inbound requests
    logger.info(f"Webhook request received - Method: {request.method}, Path: {request.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # Always return 200 OK for non-POST requests (GET, HEAD, OPTIONS)
    if request.method != 'POST':
        from django.http import HttpResponse
        logger.info(f"Non-POST request ({request.method}) - returning 200 OK")
        response = HttpResponse('OK', content_type='text/plain', status=200)
        
        # Save to database
        WebhookLog.objects.create(
            method=request.method,
            path=request.path,
            headers=dict(request.headers),
            body='',
            response_status=response.status_code,
            response_body='OK',
            success=True,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        
        return response
    
    if request.method == 'POST':
        # Log request body
        body_unicode = request.body.decode('utf-8')
        logger.info(f"POST body: {body_unicode}")
        
        try:
            # Try to parse JSON data from the request body
            try:
                import json
                if body_unicode:
                    data = json.loads(body_unicode)
                else:
                    data = {}
            except json.JSONDecodeError:
                # Fall back to form data if not valid JSON
                data = request.POST.dict()
                logger.info(f"Parsed as form data: {data}")
            
            # Support direct API calls with specific parameters
            if 'webinar_date_id' in data or 'webinar_date_id' in request.GET:
                logger.info(f"Processing as direct webhook call")
                result = handle_direct_webhook(request, data)
                logger.info(f"Direct webhook result - Status: {result.status_code}")
                
                # Save to database
                response_body = result.content.decode('utf-8') if hasattr(result, 'content') else ''
                WebhookLog.objects.create(
                    method=request.method,
                    path=request.path,
                    headers=dict(request.headers),
                    body=body_unicode,
                    response_status=result.status_code,
                    response_body=response_body,
                    success=(result.status_code < 400),
                    error_message='' if result.status_code < 400 else 'Direct webhook error',
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                
                return result
            
            # Process Kajabi webhook data
            logger.info(f"Processing Kajabi webhook data")
            from .utils import process_kajabi_webhook
            success, message, attendee_id = process_kajabi_webhook(data, request)
            
            if success:
                logger.info(f"Webhook processed successfully - Message: {message}, Attendee ID: {attendee_id}")
                response_data = {
                    'status': 'success',
                    'message': message,
                    'attendee_id': attendee_id
                }
                response = JsonResponse(response_data)
                
                # Save to database
                WebhookLog.objects.create(
                    method=request.method,
                    path=request.path,
                    headers=dict(request.headers),
                    body=body_unicode,
                    response_status=response.status_code,
                    response_body=json.dumps(response_data),
                    success=True,
                    error_message='',
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                
                return response
            else:
                logger.warning(f"Webhook processing failed - Message: {message}")
                response_data = {
                    'status': 'error',
                    'message': message
                }
                response = JsonResponse(response_data, status=400)
                
                # Save to database
                WebhookLog.objects.create(
                    method=request.method,
                    path=request.path,
                    headers=dict(request.headers),
                    body=body_unicode,
                    response_status=response.status_code,
                    response_body=json.dumps(response_data),
                    success=False,
                    error_message=message,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                
                return response
            
        except Exception as e:
            import traceback
            error_message = f"Unhandled exception: {str(e)}\n{traceback.format_exc()}"
            
            # Log the error (using the same logger instance)
            logger.error(f"Webhook exception - {error_message}")
            logger.error(f"Request data that caused error: {data}")
            
            # Send error notification email
            from .utils import send_webhook_error_email
            try:
                send_webhook_error_email(
                    "info@awesometechtraining.com", 
                    error_message, 
                    {'request_body': request.body.decode('utf-8') if request.body else None,
                     'request_POST': dict(request.POST),
                     'request_GET': dict(request.GET)}
                )
            except Exception as email_error:
                logger.error(f"Failed to send error email: {str(email_error)}")
            
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            response = JsonResponse(response_data, status=500)
            
            # Save to database
            WebhookLog.objects.create(
                method=request.method,
                path=request.path,
                headers=dict(request.headers),
                body=body_unicode,
                response_status=response.status_code,
                response_body=json.dumps(response_data),
                success=False,
                error_message=error_message,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
            return response
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


@csrf_exempt
def download_webhook(request):
    """Webhook endpoint for download form submissions."""
    import logging
    import time
    from .models import WebhookLog
    
    logger = logging.getLogger('webinars')
    start_time = time.time()
    
    # Log all inbound requests
    logger.info(f"Download webhook request received - Method: {request.method}, Path: {request.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # Always return 200 OK for non-POST requests (GET, HEAD, OPTIONS)
    if request.method != 'POST':
        from django.http import HttpResponse
        logger.info(f"Non-POST request ({request.method}) - returning 200 OK")
        response = HttpResponse('OK', content_type='text/plain', status=200)
        
        # Save to database
        WebhookLog.objects.create(
            method=request.method,
            path=request.path,
            headers=dict(request.headers),
            body='',
            response_status=response.status_code,
            response_body='OK',
            success=True,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        
        return response
    
    if request.method == 'POST':
        # Log request body
        body_unicode = request.body.decode('utf-8')
        logger.info(f"POST body: {body_unicode}")
        
        try:
            # Try to parse JSON data from the request body
            try:
                import json
                if body_unicode:
                    data = json.loads(body_unicode)
                else:
                    data = {}
            except json.JSONDecodeError:
                # Fall back to form data if not valid JSON
                data = request.POST.dict()
                logger.info(f"Parsed as form data: {data}")
            
            # Check if this is a Kajabi webhook with nested payload
            if 'event' in data and 'payload' in data:
                # Kajabi webhook format
                payload = data.get('payload', {})
                first_name = payload.get('First Name', '')
                last_name = payload.get('Surname', '') or payload.get('Last Name', '')  # Optional
                email = payload.get('Email', '')
                form_title = payload.get('form_title', '')
                organization = (payload.get('custom_field_organisation') or 
                              payload.get('Organisation') or 
                              payload.get('Organization') or 
                              payload.get('organisation') or 
                              payload.get('organization') or '')
            else:
                # Direct API call format
                first_name = data.get('first_name', '')
                last_name = data.get('last_name', '')  # Optional
                email = data.get('email', '')
                form_title = data.get('form_title', '')
                organization = data.get('organization', '')
            
            # Validate required fields
            if not all([first_name, email, form_title]):
                logger.warning(f"Download webhook missing required fields - first_name: '{first_name}', email: '{email}', form_title: '{form_title}'")
                response_data = {
                    'status': 'error',
                    'message': 'Missing required fields: first_name, email, form_title'
                }
                response = JsonResponse(response_data, status=400)
                
                # Save to database
                WebhookLog.objects.create(
                    method=request.method,
                    path=request.path,
                    headers=dict(request.headers),
                    body=body_unicode,
                    response_status=response.status_code,
                    response_body=json.dumps(response_data),
                    success=False,
                    error_message='Missing required fields',
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                
                return response
            
            # Create the download record
            download = Download.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                form_title=form_title,
                payload=data,
                organization=organization,  # Organization extracted above
                salesforce_sync_pending=True  # Mark for Salesforce sync
            )
            
            logger.info(f"Created download record {download.id} for {email} - {form_title}")
            
            response_data = {
                'status': 'success',
                'message': f'Download recorded for {email}',
                'download_id': download.id
            }
            response = JsonResponse(response_data)
            
            # Save to database
            WebhookLog.objects.create(
                method=request.method,
                path=request.path,
                headers=dict(request.headers),
                body=body_unicode,
                response_status=response.status_code,
                response_body=json.dumps(response_data),
                success=True,
                error_message='',
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
            return response
            
        except Exception as e:
            import traceback
            error_message = f"Unhandled exception: {str(e)}\n{traceback.format_exc()}"
            
            # Log the error
            logger.error(f"Download webhook exception - {error_message}")
            logger.error(f"Request data that caused error: {data}")
            
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            response = JsonResponse(response_data, status=500)
            
            # Save to database
            WebhookLog.objects.create(
                method=request.method,
                path=request.path,
                headers=dict(request.headers),
                body=body_unicode,
                response_status=response.status_code,
                response_body=json.dumps(response_data),
                success=False,
                error_message=error_message,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
            return response
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


def handle_direct_webhook(request, data):
    """Handle direct webhook API calls with specific parameters."""
    import logging
    logger = logging.getLogger('webinars')
    
    # Get data from either JSON body, POST data, or query parameters
    params = {**request.GET.dict(), **data}
    logger.info(f"Direct webhook parameters: {params}")
    
    webinar_date_id = params.get('webinar_date_id')
    first_name = params.get('first_name')
    last_name = params.get('last_name')
    email = params.get('email')
    organization = params.get('organization', '')
    
    # Validate required fields
    if not all([webinar_date_id, first_name, email]):
        logger.warning(f"Direct webhook missing required fields - webinar_date_id: {webinar_date_id}, first_name: {first_name}, email: {email}")
        return JsonResponse({
            'status': 'error',
            'message': 'Missing required fields: webinar_date_id, first_name, email'
        }, status=400)
    
    # Get webinar date
    try:
        webinar_date = WebinarDate.objects.get(pk=webinar_date_id, deleted_at=None)
    except WebinarDate.DoesNotExist:
        logger.warning(f"Direct webhook webinar date not found: {webinar_date_id}")
        return JsonResponse({
            'status': 'error',
            'message': f'Webinar date not found: {webinar_date_id}'
        }, status=404)
    
    # Check if this is an on-demand webinar date
    if webinar_date.on_demand:
        # For on-demand webinars, create OnDemandAttendee directly
        from .models import OnDemandAttendee
        attendee, created = OnDemandAttendee.objects.get_or_create(
            webinar=webinar_date.webinar,
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name or '',
                'organization': organization
            }
        )
        
        # If attendee existed but was deleted, restore it
        if not created and attendee.is_deleted:
            attendee.deleted_at = None
            attendee.first_name = first_name
            attendee.last_name = last_name or ''
            attendee.organization = organization
            attendee.save()
    else:
        # For scheduled webinars, create regular Attendee
        attendee, created = Attendee.objects.get_or_create(
            webinar_date=webinar_date,
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name or '',  # Default to empty string if no last name
                'organization': organization
            }
        )
        
        # If attendee existed but was deleted, restore it
        if not created and attendee.is_deleted:
            attendee.deleted_at = None
            attendee.first_name = first_name
            attendee.last_name = last_name or ''
            attendee.organization = organization
            attendee.save()
    
    # Handle activation and Zoom registration based on attendee type
    zoom_status = ""
    
    if webinar_date.on_demand:
        # For on-demand attendees, activate immediately
        if not attendee.activation_sent_at:
            try:
                from .activation_service import activate_attendee
                success, activation_message = activate_attendee(attendee)
                if success:
                    logger.info(f"Immediately activated on-demand attendee {email}: {activation_message}")
                else:
                    logger.warning(f"Failed to activate on-demand attendee {email}: {activation_message}")
            except Exception as e:
                logger.error(f"Error activating on-demand attendee {email}: {str(e)}")
        
        # Set status message for on-demand
        if attendee.activation_sent_at and attendee.activation_success:
            zoom_status = " (on-demand - activated immediately)"
        elif attendee.activation_sent_at and not attendee.activation_success:
            zoom_status = " (on-demand - activation failed)"
        else:
            zoom_status = " (on-demand - no Zoom registration needed)"
    else:
        # For scheduled attendees, try to register in Zoom if webinar has Zoom meeting ID
        if webinar_date.zoom_meeting_id and not attendee.zoom_registrant_id:
            try:
                from .zoom_service import ZoomService
                from django.utils import timezone
                
                zoom_service = ZoomService()
                result = zoom_service.register_attendee(
                    webinar_date.zoom_meeting_id,
                    first_name,
                    last_name or '',
                    email
                )
                
                if result['success']:
                    attendee.zoom_registrant_id = result['registrant_id']
                    attendee.zoom_join_url = result['join_url']
                    attendee.zoom_invite_link = result.get('invite_link', result['join_url'])
                    attendee.zoom_registered_at = timezone.now()
                    attendee.zoom_registration_error = ''
                    zoom_status = " and registered in Zoom"
                    logger.info(f"Registered attendee {email} in Zoom webinar {webinar_date.zoom_meeting_id}")
                else:
                    attendee.zoom_registration_error = result['error']
                    zoom_status = " (Zoom registration failed)"
                    logger.warning(f"Failed to register attendee {email} in Zoom: {result['error']}")
                
                attendee.save()
                
            except Exception as e:
                error_msg = f"Error registering attendee in Zoom: {str(e)}"
                attendee.zoom_registration_error = error_msg
                attendee.save()
                logger.error(error_msg)
                zoom_status = " (Zoom registration error)"
    
    status = "Created" if created else "Updated"
    
    if webinar_date.on_demand:
        # For on-demand attendees, show webinar name only (no date)
        message = f'{status} on-demand attendee for {webinar_date.webinar.name}{zoom_status}'
        logger.info(f"Direct webhook success - {status} on-demand attendee {attendee.id} for {webinar_date.webinar.name}")
    else:
        # For scheduled attendees, show webinar name and date
        message = f'{status} attendee for {webinar_date.webinar.name} on {webinar_date.date_time}{zoom_status}'
        logger.info(f"Direct webhook success - {status} attendee {attendee.id} for {webinar_date.webinar.name}")
    
    return JsonResponse({
        'status': 'success',
        'message': message,
        'attendee_id': attendee.id
    })


# Bundle Views
class BundleListView(LoginRequiredMixin, ListView):
    model = WebinarBundle
    template_name = 'webinars/bundle_list.html'
    context_object_name = 'bundles'
    
    def get_queryset(self):
        return WebinarBundle.objects.filter(deleted_at=None)


class BundleDetailView(LoginRequiredMixin, DetailView):
    model = WebinarBundle
    template_name = 'webinars/bundle_detail.html'
    context_object_name = 'bundle'
    
    def get_queryset(self):
        return WebinarBundle.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dates'] = self.object.active_dates().order_by('date')
        return context


class BundleCreateView(LoginRequiredMixin, CreateView):
    model = WebinarBundle
    form_class = WebinarBundleForm
    template_name = 'webinars/bundle_form.html'
    success_url = reverse_lazy('dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Bundle'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Bundle created successfully.')
        return super().form_valid(form)


class BundleUpdateView(LoginRequiredMixin, UpdateView):
    model = WebinarBundle
    form_class = WebinarBundleForm
    template_name = 'webinars/bundle_form.html'
    
    def get_queryset(self):
        return WebinarBundle.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Bundle'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Bundle updated successfully.')
        return super().form_valid(form)


@login_required
def bundle_delete(request, pk):
    bundle = get_object_or_404(WebinarBundle, pk=pk, deleted_at=None)
    
    if request.method == 'POST':
        bundle.soft_delete()
        messages.success(request, 'Bundle deleted successfully.')
        return redirect('dashboard')
    
    return render(request, 'webinars/bundle_confirm_delete.html', {'bundle': bundle})


# Bundle Date Views
class BundleDateDetailView(LoginRequiredMixin, DetailView):
    model = BundleDate
    template_name = 'webinars/bundle_date_detail.html'
    context_object_name = 'bundle_date'
    
    def get_queryset(self):
        return BundleDate.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attendees'] = self.object.active_attendees()
        context['webinar_dates'] = self.object.webinar_dates.filter(deleted_at=None)
        return context


class BundleDateCreateView(LoginRequiredMixin, CreateView):
    model = BundleDate
    form_class = BundleDateForm
    template_name = 'webinars/bundle_date_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bundle = get_object_or_404(WebinarBundle, pk=self.kwargs['bundle_id'], deleted_at=None)
        context['bundle'] = bundle
        context['title'] = f'Add New Date for {bundle.name}'
        return context
    
    def post(self, request, *args, **kwargs):
        # Check if this is just a date change (not a real submission)
        if '_date_changed' in request.POST:
            # Just re-render the form with the new date
            self.object = None
            form = self.get_form()
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        bundle = get_object_or_404(WebinarBundle, pk=self.kwargs['bundle_id'], deleted_at=None)
        form.instance.bundle = bundle
        messages.success(self.request, 'Bundle date created successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('bundle_detail', args=[self.kwargs['bundle_id']])


class BundleDateUpdateView(LoginRequiredMixin, UpdateView):
    model = BundleDate
    form_class = BundleDateForm
    template_name = 'webinars/bundle_date_form.html'
    
    def get_queryset(self):
        return BundleDate.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bundle'] = self.object.bundle
        context['title'] = f'Edit Date for {self.object.bundle.name}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Bundle date updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('bundle_detail', args=[self.object.bundle.id])


@login_required
def bundle_date_delete(request, pk):
    bundle_date = get_object_or_404(BundleDate, pk=pk, deleted_at=None)
    bundle_id = bundle_date.bundle.id
    
    if bundle_date.has_attendees:
        messages.error(request, 'Cannot delete a bundle date with attendees.')
        return redirect('bundle_date_detail', pk=pk)
    
    if request.method == 'POST':
        bundle_date.soft_delete()
        messages.success(request, 'Bundle date deleted successfully.')
        return redirect('bundle_detail', pk=bundle_id)
    
    return render(request, 'webinars/bundle_date_confirm_delete.html', {'bundle_date': bundle_date})


# Activation Views
@login_required
def activate_attendee_view(request, attendee_id):
    """Activate grant offer for a single attendee."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    # Try to get regular attendee first
    attendee = None
    try:
        attendee = Attendee.objects.get(pk=attendee_id, deleted_at=None)
    except Attendee.DoesNotExist:
        # Try bundle attendee
        try:
            attendee = BundleAttendee.objects.get(pk=attendee_id, deleted_at=None)
        except BundleAttendee.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Attendee not found'}, status=404)
    
    # Import and use activation service
    from .activation_service import activate_attendee
    success, message = activate_attendee(attendee)
    
    if success:
        messages.success(request, message)
        return JsonResponse({'success': True, 'message': message})
    else:
        messages.error(request, message)
        return JsonResponse({'success': False, 'message': message}, status=400)


@login_required
def activate_webinar_date_view(request, webinar_date_id):
    """Activate grant offers for all attendees of a webinar date."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    webinar_date = get_object_or_404(WebinarDate, pk=webinar_date_id, deleted_at=None)
    
    # Import and use activation service
    from .activation_service import activate_webinar_date_attendees
    success_count, failure_count, activation_messages = activate_webinar_date_attendees(webinar_date)
    
    # Create summary message
    total = success_count + failure_count
    if total == 0:
        message = "No attendees found to activate."
    else:
        message = f"Processed {total} attendees: {success_count} successful, {failure_count} failed."
    
    if failure_count == 0 and success_count > 0:
        messages.success(request, message)
        return JsonResponse({
            'success': True, 
            'message': message,
            'details': activation_messages,
            'success_count': success_count,
            'failure_count': failure_count
        })
    elif success_count > 0:
        messages.warning(request, message)
        return JsonResponse({
            'success': True, 
            'message': message,
            'details': activation_messages,
            'success_count': success_count,
            'failure_count': failure_count
        })
    else:
        messages.error(request, message)
        return JsonResponse({
            'success': False, 
            'message': message,
            'details': activation_messages,
            'success_count': success_count,
            'failure_count': failure_count
        }, status=400)


@csrf_exempt
def cron_activate_pending(request):
    """
    Cron job endpoint to activate all pending attendees.
    Should be called periodically (e.g., every hour) by a cron job.
    """
    if request.method not in ['GET', 'POST']:
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    # Import and use activation service
    from .activation_service import activate_pending_attendees
    success_count, failure_count, activation_messages = activate_pending_attendees()
    
    # Create summary message
    total = success_count + failure_count
    if total == 0:
        message = "No attendees found needing activation."
    else:
        message = f"Processed {total} attendees: {success_count} successful, {failure_count} failed."
    
    # Log the results
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Cron activation completed: {message}")
    
    return JsonResponse({
        'success': True,
        'message': message,
        'details': activation_messages,
        'success_count': success_count,
        'failure_count': failure_count,
        'timestamp': timezone.now().isoformat()
    })


@login_required
def activate_bundle_date_view(request, bundle_date_id):
    """Activate grant offers for all attendees of a bundle date."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    bundle_date = get_object_or_404(BundleDate, pk=bundle_date_id, deleted_at=None)
    
    # Import and use activation service
    from .activation_service import KajabiActivationService
    service = KajabiActivationService()
    
    attendees = bundle_date.active_attendees()
    success_count = 0
    failure_count = 0
    activation_messages = []
    
    for attendee in attendees:
        # Skip if already activated
        if attendee.activation_sent_at:
            activation_messages.append(f"Skipped {attendee.email} (already activated)")
            continue
        
        success, message = service.activate_attendee(attendee)
        if success:
            success_count += 1
        else:
            failure_count += 1
        activation_messages.append(message)
    
    # Create summary message
    total = success_count + failure_count
    if total == 0:
        message = "No attendees found to activate."
    else:
        message = f"Processed {total} attendees: {success_count} successful, {failure_count} failed."
    
    if failure_count == 0 and success_count > 0:
        messages.success(request, message)
        return JsonResponse({
            'success': True, 
            'message': message,
            'details': activation_messages,
            'success_count': success_count,
            'failure_count': failure_count
        })
    elif success_count > 0:
        messages.warning(request, message)
        return JsonResponse({
            'success': True, 
            'message': message,
            'details': activation_messages,
            'success_count': success_count,
            'failure_count': failure_count
        })
    else:
        messages.error(request, message)
        return JsonResponse({
            'success': False, 
            'message': message,
            'details': activation_messages,
            'success_count': success_count,
            'failure_count': failure_count
        }, status=400)


@login_required
def send_calendar_invite_view(request, webinar_date_id):
    """Send calendar invite for a webinar date."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    webinar_date = get_object_or_404(WebinarDate, pk=webinar_date_id, deleted_at=None)
    
    try:
        # Import and use MS365 service
        from .ms365_service import MS365CalendarService
        ms365_service = MS365CalendarService()
        
        # Send calendar invite
        success, message = ms365_service.send_manual_calendar_invite(webinar_date)
        
        if success:
            messages.success(request, message)
            return JsonResponse({'success': True, 'message': message})
        else:
            messages.error(request, message)
            return JsonResponse({'success': False, 'message': message}, status=400)
            
    except Exception as e:
        error_msg = f"Error sending calendar invite: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({'success': False, 'message': error_msg}, status=500)


# Webhook Log Views
@login_required
def webhook_log_list(request):
    """List all webhook logs with pagination."""
    from .models import WebhookLog
    from django.core.paginator import Paginator
    
    webhook_logs = WebhookLog.objects.all()
    
    # Filter by success/failure if requested
    status_filter = request.GET.get('status')
    if status_filter == 'success':
        webhook_logs = webhook_logs.filter(success=True)
    elif status_filter == 'failure':
        webhook_logs = webhook_logs.filter(success=False)
    
    # Filter by method if requested
    method_filter = request.GET.get('method')
    if method_filter:
        webhook_logs = webhook_logs.filter(method=method_filter)
    
    # Paginate results
    paginator = Paginator(webhook_logs, 50)  # Show 50 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'webinars/webhook_log_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'method_filter': method_filter,
    })


@login_required
def webhook_log_detail(request, pk):
    """View details of a specific webhook log."""
    from .models import WebhookLog
    
    webhook_log = get_object_or_404(WebhookLog, pk=pk)
    
    return render(request, 'webinars/webhook_log_detail.html', {
        'webhook_log': webhook_log,
    })


@login_required
def webhook_log_delete(request, pk):
    """Delete a specific webhook log."""
    from .models import WebhookLog
    
    if request.method == 'POST':
        webhook_log = get_object_or_404(WebhookLog, pk=pk)
        webhook_log.delete()
        messages.success(request, 'Webhook log deleted successfully.')
        return redirect('webhook_log_list')
    
    return redirect('webhook_log_list')


@login_required
def webhook_log_clear_all(request):
    """Clear all webhook logs."""
    from .models import WebhookLog
    
    if request.method == 'POST':
        count = WebhookLog.objects.count()
        WebhookLog.objects.all().delete()
        messages.success(request, f'Cleared {count} webhook logs.')
        return redirect('webhook_log_list')
    
    return redirect('webhook_log_list')


@login_required
def sync_attendee_salesforce(request, attendee_id):
    """Manually sync an attendee to Salesforce."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    # Try to find the attendee in different models
    attendee = None
    attendee_type = None
    
    # Check regular attendees first
    try:
        attendee = Attendee.objects.get(pk=attendee_id, deleted_at=None)
        attendee_type = "Attendee"
    except Attendee.DoesNotExist:
        # Try on-demand attendees
        try:
            attendee = OnDemandAttendee.objects.get(pk=attendee_id, deleted_at=None)
            attendee_type = "OnDemandAttendee"
        except OnDemandAttendee.DoesNotExist:
            # Try bundle attendees
            try:
                attendee = BundleAttendee.objects.get(pk=attendee_id, deleted_at=None)
                attendee_type = "BundleAttendee"
            except BundleAttendee.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Attendee not found'}, status=404)
    
    try:
        from .salesforce_service import SalesforceService
        
        sf_service = SalesforceService()
        success, message = sf_service.sync_attendee(attendee)
        
        if success:
            messages.success(request, f'Successfully synced {attendee.email} to Salesforce')
            return JsonResponse({'success': True, 'message': message})
        else:
            messages.error(request, f'Failed to sync {attendee.email} to Salesforce: {message}')
            return JsonResponse({'success': False, 'message': message}, status=400)
            
    except Exception as e:
        error_msg = f"Error syncing to Salesforce: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({'success': False, 'message': error_msg}, status=500)


@login_required
def register_attendee_zoom(request, attendee_id):
    """Manually register an attendee in Zoom."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    attendee = get_object_or_404(Attendee, pk=attendee_id, deleted_at=None)
    
    # Check if webinar date has Zoom meeting ID
    if not attendee.webinar_date.zoom_meeting_id:
        return JsonResponse({
            'success': False, 
            'message': 'No Zoom webinar ID configured for this webinar date'
        }, status=400)
    
    # Check if already registered
    if attendee.zoom_registrant_id:
        return JsonResponse({
            'success': False, 
            'message': 'Attendee is already registered in Zoom'
        }, status=400)
    
    try:
        from .zoom_service import ZoomService
        from django.utils import timezone
        
        zoom_service = ZoomService()
        result = zoom_service.register_attendee(
            attendee.webinar_date.zoom_meeting_id,
            attendee.first_name,
            attendee.last_name,
            attendee.email
        )
        
        if result['success']:
            attendee.zoom_registrant_id = result['registrant_id']
            attendee.zoom_join_url = result['join_url']
            attendee.zoom_invite_link = result.get('invite_link', result['join_url'])
            attendee.zoom_registered_at = timezone.now()
            attendee.zoom_registration_error = ''
            attendee.save()
            
            messages.success(request, f'Successfully registered {attendee.email} in Zoom')
            return JsonResponse({
                'success': True, 
                'message': f'Successfully registered {attendee.email} in Zoom',
                'registrant_id': result['registrant_id']
            })
        else:
            attendee.zoom_registration_error = result['error']
            attendee.save()
            
            messages.error(request, f'Failed to register {attendee.email} in Zoom: {result["error"]}')
            return JsonResponse({
                'success': False, 
                'message': f'Failed to register in Zoom: {result["error"]}'
            }, status=400)
            
    except Exception as e:
        error_msg = f"Error registering attendee in Zoom: {str(e)}"
        attendee.zoom_registration_error = error_msg
        attendee.save()
        
        messages.error(request, error_msg)
        return JsonResponse({
            'success': False, 
            'message': error_msg
        }, status=500)


# Forthcoming Webinars View
@login_required
def forthcoming_webinars(request):
    """Display all forthcoming webinars across the system."""
    from django.utils import timezone
    from django.db.models import Q
    
    # Get all future webinar dates (excluding on-demand and deleted)
    current_time = timezone.now()
    webinar_dates = WebinarDate.objects.filter(
        deleted_at=None,
        webinar__deleted_at=None,  # Also exclude dates from deleted webinars
        on_demand=False,
        date_time__gte=current_time
    ).select_related('webinar').order_by('date_time')
    
    # Get bundle dates with future webinars
    bundle_dates = BundleDate.objects.filter(
        deleted_at=None,
        bundle__deleted_at=None,  # Also exclude dates from deleted bundles
        date__gte=current_time.date()
    ).select_related('bundle').prefetch_related('webinar_dates').order_by('date')
    
    # Combine and sort all events
    events = []
    
    # Add webinar dates
    for date in webinar_dates:
        events.append({
            'type': 'webinar',
            'title': date.webinar.name,
            'date_time': date.date_time,
            'zoom_meeting_id': date.zoom_meeting_id,
            'attendee_count': date.total_attendee_count,
            'detail_url': date.get_absolute_url(),
            'webinar_url': date.webinar.get_absolute_url()
        })
    
    # Add bundle dates
    for bundle in bundle_dates:
        # Find the earliest webinar time on this date
        webinar_dates_on_day = bundle.webinar_dates.filter(
            deleted_at=None,
            date_time__date=bundle.date
        ).order_by('date_time')
        
        if webinar_dates_on_day.exists():
            first_time = webinar_dates_on_day.first().date_time
        else:
            # If no webinars on this date, use 9am as default
            first_time = timezone.make_aware(
                timezone.datetime.combine(bundle.date, timezone.datetime.min.time().replace(hour=9))
            )
        
        events.append({
            'type': 'bundle',
            'title': bundle.bundle.name,
            'date_time': first_time,
            'zoom_meeting_id': None,  # Bundles don't have direct Zoom IDs
            'attendee_count': bundle.attendee_count,
            'detail_url': bundle.get_absolute_url(),
            'webinar_count': bundle.webinar_dates.filter(deleted_at=None).count()
        })
    
    # Sort all events by date_time
    events.sort(key=lambda x: x['date_time'])
    
    return render(request, 'webinars/forthcoming_webinars.html', {
        'events': events,
        'current_time': current_time
    })


# Download Views
@login_required
def download_list(request):
    """Display all downloads with pagination."""
    from django.core.paginator import Paginator
    
    downloads = Download.objects.filter(deleted_at=None).order_by('-created_at')
    
    # Filter by form title if requested
    form_title_filter = request.GET.get('form_title')
    if form_title_filter:
        downloads = downloads.filter(form_title__icontains=form_title_filter)
    
    # Filter by Salesforce sync status if requested
    sync_status_filter = request.GET.get('sync_status')
    if sync_status_filter == 'synced':
        downloads = downloads.exclude(salesforce_synced_at=None)
    elif sync_status_filter == 'pending':
        downloads = downloads.filter(salesforce_sync_pending=True, salesforce_synced_at=None)
    elif sync_status_filter == 'failed':
        downloads = downloads.exclude(salesforce_sync_error='')
    
    # Paginate results
    paginator = Paginator(downloads, 50)  # Show 50 downloads per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'webinars/download_list.html', {
        'page_obj': page_obj,
        'form_title_filter': form_title_filter,
        'sync_status_filter': sync_status_filter,
    })


@login_required
def download_detail(request, pk):
    """View details of a specific download."""
    download = get_object_or_404(Download, pk=pk, deleted_at=None)
    
    return render(request, 'webinars/download_detail.html', {
        'download': download,
    })


@login_required
def sync_download_salesforce(request, download_id):
    """Manually sync a download to Salesforce."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    download = get_object_or_404(Download, pk=download_id, deleted_at=None)
    
    try:
        from .salesforce_service import SalesforceService
        
        sf_service = SalesforceService()
        success, message = sf_service.sync_download(download)
        
        if success:
            messages.success(request, f'Successfully synced {download.email} to Salesforce')
            return JsonResponse({'success': True, 'message': message})
        else:
            messages.error(request, f'Failed to sync {download.email} to Salesforce: {message}')
            return JsonResponse({'success': False, 'message': message}, status=400)
            
    except Exception as e:
        error_msg = f"Error syncing to Salesforce: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({'success': False, 'message': error_msg}, status=500)


# Clinic Booking Views
@login_required
def clinic_booking_list(request):
    """Display all clinic bookings with pagination."""
    from django.core.paginator import Paginator
    
    clinic_bookings = ClinicBooking.objects.filter(deleted_at=None).order_by('-created_at')
    
    # Filter by organization if requested
    organization_filter = request.GET.get('organization')
    if organization_filter:
        clinic_bookings = clinic_bookings.filter(organization__icontains=organization_filter)
    
    # Filter by Salesforce sync status if requested
    sync_status_filter = request.GET.get('sync_status')
    if sync_status_filter == 'synced':
        clinic_bookings = clinic_bookings.exclude(salesforce_synced_at=None)
    elif sync_status_filter == 'pending':
        clinic_bookings = clinic_bookings.filter(salesforce_sync_pending=True, salesforce_synced_at=None)
    elif sync_status_filter == 'failed':
        clinic_bookings = clinic_bookings.exclude(salesforce_sync_error='')
    
    # Filter by date range if requested
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        try:
            from datetime import datetime
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            clinic_bookings = clinic_bookings.filter(clinic_date__date__gte=date_from_parsed)
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import datetime
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            clinic_bookings = clinic_bookings.filter(clinic_date__date__lte=date_to_parsed)
        except ValueError:
            pass
    
    # Paginate results
    paginator = Paginator(clinic_bookings, 50)  # Show 50 bookings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'webinars/clinic_booking_list.html', {
        'page_obj': page_obj,
        'organization_filter': organization_filter,
        'sync_status_filter': sync_status_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def clinic_booking_detail(request, pk):
    """View details of a specific clinic booking."""
    clinic_booking = get_object_or_404(ClinicBooking, pk=pk, deleted_at=None)
    
    return render(request, 'webinars/clinic_booking_detail.html', {
        'clinic_booking': clinic_booking,
    })


@login_required
def sync_clinic_booking_salesforce(request, clinic_booking_id):
    """Manually sync a clinic booking to Salesforce."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    clinic_booking = get_object_or_404(ClinicBooking, pk=clinic_booking_id, deleted_at=None)
    
    try:
        from .salesforce_service import SalesforceService
        
        sf_service = SalesforceService()
        success, message = sf_service.sync_clinic_booking(clinic_booking)
        
        if success:
            messages.success(request, f'Successfully synced {clinic_booking.email} to Salesforce')
            return JsonResponse({'success': True, 'message': message})
        else:
            messages.error(request, f'Failed to sync {clinic_booking.email} to Salesforce: {message}')
            return JsonResponse({'success': False, 'message': message}, status=400)
            
    except Exception as e:
        error_msg = f"Error syncing to Salesforce: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({'success': False, 'message': error_msg}, status=500)


@csrf_exempt
def clinic_booking_webhook(request):
    """Webhook endpoint for clinic booking form submissions."""
    import logging
    import time
    from .models import WebhookLog
    
    logger = logging.getLogger("webinars")
    start_time = time.time()
    
    # Log all inbound requests
    logger.info(f"Clinic booking webhook request received - Method: {request.method}, Path: {request.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # Always return 200 OK for non-POST requests (GET, HEAD, OPTIONS)
    if request.method != "POST":
        from django.http import HttpResponse
        logger.info(f"Non-POST request ({request.method}) - returning 200 OK")
        response = HttpResponse("OK", content_type="text/plain", status=200)
        
        # Save to database
        WebhookLog.objects.create(
            method=request.method,
            path=request.path,
            headers=dict(request.headers),
            body="",
            response_status=response.status_code,
            response_body="OK",
            success=True,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        
        return response
    
    if request.method == "POST":
        # Log request body
        body_unicode = request.body.decode("utf-8")
        logger.info(f"POST body: {body_unicode}")
        
        try:
            # Try to parse JSON data from the request body
            try:
                import json
                if body_unicode:
                    data = json.loads(body_unicode)
                else:
                    data = {}
            except json.JSONDecodeError:
                # Fall back to form data if not valid JSON
                data = request.POST.dict()
                logger.info(f"Parsed as form data: {data}")
            
            # Extract fields based on expected structure
            # For now using placeholders as requested
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "") or data.get("surname", "")
            email = data.get("email", "")
            organization = data.get("organization", "") or data.get("organisation", "")
            clinic_date = data.get("clinic_date", "")  # Placeholder format
            website = data.get("website", "")  # Placeholder field
            question = data.get("question", "")
            
            # Validate required fields
            if not all([first_name, last_name, email, clinic_date, question]):
                logger.warning(f"Clinic booking webhook missing required fields - first_name: \"{first_name}\", last_name: \"{last_name}\", email: \"{email}\", clinic_date: \"{clinic_date}\", question: \"{question}\"")
                response_data = {
                    "status": "error",
                    "message": "Missing required fields: first_name, last_name, email, clinic_date, question"
                }
                response = JsonResponse(response_data, status=400)
                
                # Save to database
                WebhookLog.objects.create(
                    method=request.method,
                    path=request.path,
                    headers=dict(request.headers),
                    body=body_unicode,
                    response_status=response.status_code,
                    response_body=json.dumps(response_data),
                    success=False,
                    error_message="Missing required fields",
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                
                return response
            
            # Parse clinic_date - for now treating as placeholder
            # TODO: Implement proper date parsing once format is defined
            clinic_datetime = timezone.now()  # Placeholder
            try:
                from dateutil import parser
                clinic_datetime = parser.parse(clinic_date)
                if timezone.is_naive(clinic_datetime):
                    clinic_datetime = timezone.make_aware(clinic_datetime)
            except Exception as e:
                logger.warning(f"Could not parse clinic date \"{clinic_date}\": {e}")
                # Keep the default datetime for now
            
            # Create the clinic booking record
            clinic_booking = ClinicBooking.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                organization=organization,
                clinic_date=clinic_datetime,
                website=website,
                question=question,
                salesforce_sync_pending=True  # Mark for Salesforce sync
            )
            
            logger.info(f"Created clinic booking record {clinic_booking.id} for {email} - {clinic_datetime}")
            
            # Trigger Zoom meeting creation and calendar invites
            try:
                from .utils import process_clinic_booking
                process_clinic_booking(clinic_booking)
                logger.info(f"Processed clinic booking {clinic_booking.id} - Zoom and calendar processing initiated")
            except Exception as e:
                logger.error(f"Error processing clinic booking {clinic_booking.id}: {e}")
                # Do not fail the webhook - just log the error
            
            response_data = {
                "status": "success",
                "message": f"Clinic booking recorded for {email}",
                "booking_id": clinic_booking.id
            }
            response = JsonResponse(response_data)
            
            # Save to database
            WebhookLog.objects.create(
                method=request.method,
                path=request.path,
                headers=dict(request.headers),
                body=body_unicode,
                response_status=response.status_code,
                response_body=json.dumps(response_data),
                success=True,
                error_message="",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
            return response
            
        except Exception as e:
            import traceback
            error_message = f"Unhandled exception: {str(e)}\n{traceback.format_exc()}"
            
            # Log the error
            logger.error(f"Clinic booking webhook exception - {error_message}")
            logger.error(f"Request data that caused error: {data}")
            
            response_data = {
                "status": "error",
                "message": str(e)
            }
            response = JsonResponse(response_data, status=500)
            
            # Save to database
            WebhookLog.objects.create(
                method=request.method,
                path=request.path,
                headers=dict(request.headers),
                body=body_unicode,
                response_status=response.status_code,
                response_body=json.dumps(response_data),
                success=False,
                error_message=error_message,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
            return response
    
    return JsonResponse({
        "status": "error",
        "message": "Method not allowed"
    }, status=405)

