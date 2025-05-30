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

from .models import Webinar, WebinarDate, Attendee, WebinarBundle, BundleDate, BundleAttendee
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
class WebinarListView(LoginRequiredMixin, ListView):
    model = Webinar
    template_name = 'webinars/webinar_list.html'
    context_object_name = 'webinars'
    
    def get_queryset(self):
        return Webinar.objects.filter(deleted_at=None)


class WebinarDetailView(LoginRequiredMixin, DetailView):
    model = Webinar
    template_name = 'webinars/webinar_detail.html'
    context_object_name = 'webinar'
    
    def get_queryset(self):
        return Webinar.objects.filter(deleted_at=None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dates'] = self.object.active_dates().order_by('date_time')
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
    # Always return 200 OK for non-POST requests (GET, HEAD, OPTIONS)
    if request.method != 'POST':
        from django.http import HttpResponse
        return HttpResponse('OK', content_type='text/plain', status=200)
    
    if request.method == 'POST':
        try:
            # Try to parse JSON data from the request body
            try:
                import json
                body_unicode = request.body.decode('utf-8')
                if body_unicode:
                    data = json.loads(body_unicode)
                else:
                    data = {}
            except json.JSONDecodeError:
                # Fall back to form data if not valid JSON
                data = request.POST.dict()
            
            # Support direct API calls with specific parameters
            if 'webinar_date_id' in data or 'webinar_date_id' in request.GET:
                return handle_direct_webhook(request, data)
            
            # Process Kajabi webhook data
            from .utils import process_kajabi_webhook
            success, message, attendee_id = process_kajabi_webhook(data, request)
            
            if success:
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'attendee_id': attendee_id
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': message
                }, status=400)
            
        except Exception as e:
            import traceback
            error_message = f"Unhandled exception: {str(e)}\n{traceback.format_exc()}"
            
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(error_message)
            
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
            
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


def handle_direct_webhook(request, data):
    """Handle direct webhook API calls with specific parameters."""
    # Get data from either JSON body, POST data, or query parameters
    params = {**request.GET.dict(), **data}
    
    webinar_date_id = params.get('webinar_date_id')
    first_name = params.get('first_name')
    last_name = params.get('last_name')
    email = params.get('email')
    
    # Validate required fields
    if not all([webinar_date_id, first_name, email]):
        return JsonResponse({
            'status': 'error',
            'message': 'Missing required fields: webinar_date_id, first_name, email'
        }, status=400)
    
    # Get webinar date
    try:
        webinar_date = WebinarDate.objects.get(pk=webinar_date_id, deleted_at=None)
    except WebinarDate.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f'Webinar date not found: {webinar_date_id}'
        }, status=404)
    
    # Create or get attendee
    attendee, created = Attendee.objects.get_or_create(
        webinar_date=webinar_date,
        email=email,
        defaults={
            'first_name': first_name,
            'last_name': last_name or ''  # Default to empty string if no last name
        }
    )
    
    # If attendee existed but was deleted, restore it
    if not created and attendee.is_deleted:
        attendee.deleted_at = None
        attendee.first_name = first_name
        attendee.last_name = last_name or ''
        attendee.save()
    
    status = "Created" if created else "Updated"
    return JsonResponse({
        'status': 'success',
        'message': f'{status} attendee for {webinar_date.webinar.name} on {webinar_date.date_time}',
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
