import csv
import json
import logging
import os
from datetime import datetime, timedelta

from django.utils import timezone
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponse, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.dateparse import parse_datetime

from zoneinfo import ZoneInfo
from .models import Workshop, WorkshopInvitation, Participant
from .forms import WorkshopForm, FileFieldForm, ImportDataForm
from accounts.models import CustomUser
from api.models import AirQualityRecord, MobilityMode
from devices.models import Device
from main import settings
from main.util import workshop_add_image


logger = logging.getLogger('myapp')


class WorkshopListView(ListView):
    model = Workshop
    context_object_name = 'workshops'
    template_name = 'workshops/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Upcoming workshops: those with end_date in the future, sorted descending (latest first)
        upcoming_qs = Workshop.objects.filter(
            end_date__gt=timezone.now(), public=True
        ).order_by('-end_date')
        paginator_upcoming = Paginator(upcoming_qs, 10)
        page_upcoming = self.request.GET.get('page_upcoming')
        try:
            upcoming_page = paginator_upcoming.page(page_upcoming)
        except PageNotAnInteger:
            upcoming_page = paginator_upcoming.page(1)
        except EmptyPage:
            upcoming_page = paginator_upcoming.page(paginator_upcoming.num_pages)
        context['upcoming_workshops'] = upcoming_page

        # Past workshops: those with end_date in the past, sorted descending (most recent first)
        past_qs = Workshop.objects.filter(
            end_date__lte=timezone.now(), public=True
        ).order_by('-end_date')
        paginator_past = Paginator(past_qs, 10)
        page_past = self.request.GET.get('page_past')
        try:
            past_page = paginator_past.page(page_past)
        except PageNotAnInteger:
            past_page = paginator_past.page(1)
        except EmptyPage:
            past_page = paginator_past.page(paginator_past.num_pages)
        context['past_workshops'] = past_page
        
        return context


class WorkshopDetailView(DetailView):
    model = Workshop
    context_object_name = 'workshop'
    template_name = 'workshops/detail.html'

    # def get_queryset(self):
    #     """
    #     This method is overridden to only include workshops that are public.
    #     """
    #     return Workshop.objects.filter(public=True)
    
    def get_object(self, queryset=None):
        """
        This method is overridden to provide additional checks for the workshop's visibility.
        If the requested workshop is not public, it raises a 404.
        """
        try:
            queryset = self.get_queryset() if queryset is None else queryset
            obj = super().get_object(queryset=queryset)
        
        except Workshop.DoesNotExist:
            raise Http404("Workshop nicht gefunden.")
        
        if not obj.public:
            if not self.request.user.is_superuser and not obj.users.filter(id = self.request.user.id).exists():
                raise Http404("Workshop nicht gefunden.")

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        # description, time, lat, lon, url
        images = []
        for workshop_image in self.object.workshop_images.all():
            images.append([
                workshop_image.time_created.astimezone(ZoneInfo("Europe/Vienna")).strftime("%d.%m.%Y %H:%M"),
                workshop_image.location.coordinates.x,
                workshop_image.location.coordinates.y,
                os.path.join(settings.MEDIA_URL, workshop_image.image.name)
            ])

        context['is_owner'] = self.request.user.is_superuser or self.request.user == self.object.owner 
        context['images'] = images
        return context

class WorkshopManagementView(LoginRequiredMixin, DetailView):
    model = Workshop
    template_name = 'workshops/management.html'
    context_object_name = 'workshop'

    def get_object(self, queryset = None):
        workshop = super().get_object(queryset)
        if self.request.user.is_superuser:
            return workshop 
        if workshop.owner != self.request.user:
            raise PermissionDenied("Only members can view this Organization")
        return workshop


@login_required
def remove_user_from_workshop(request, workshop_id, user_id):
    workshop = get_object_or_404(Workshop, name=workshop_id)
    user = get_object_or_404(CustomUser, id=user_id)

    # Ensure the user performing the action has permission
    if not request.user.is_superuser and request.user != workshop.owner:
        messages.error(request, "You do not have permission to remove users from this workshop.")
        return redirect('workshop-detail', workshop_id)
    
    # the owner cannot be removed
    if user == workshop.owner:
        messages.error(request, "The Owner of the Workshop cannot be removed")
        return redirect('workshop-management', workshop_id)

    workshop.users.remove(user)
    return redirect('workshop-management', workshop_id)


@login_required
def invite_user_to_workshop(request, workshop_id):
    workshop = get_object_or_404(Workshop, name=workshop_id)
    email = request.POST.get('email')
    
    # Check permissions
    if not request.user.is_superuser and request.user != Workshop.owner:
        messages.error(request, "You do not have permission to invite users to this organization.")
        return redirect('workshop-detail', workshop.pk)

    user = CustomUser.objects.filter(email=email).first()

    if user:
        workshop.users.add(user)
        messages.success(request, f"{email} has been added to the organization.")
    else:
        # Check if invitation already exists
        invitation = WorkshopInvitation.objects.filter(email=email, workshop=workshop).first()

        if not invitation:
            # Create an invitation
            invitation = WorkshopInvitation(
                expiring_date=None,
                email=email,
                workshop=workshop,
            )
            invitation.save()

        # Generate the email body from a template
        context = {
            'workshop': workshop,
            'registration_link': ''
        }
        message_body = render_to_string('workshops/email/invite_user_to_workshop.txt', context)

        # Send the email
        send_mail(
            subject=f"You've been invited to join {workshop.name}",
            message=message_body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )

        messages.success(request, f"An invitation has been sent to {email}.")

    return redirect('workshop-management', workshop.pk)


class WorkshopMyView(LoginRequiredMixin, ListView):
    model = Workshop
    template_name = 'workshops/my.html'
    context_object_name = 'workshops'
    paginate_by = 10 

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Workshop.objects.filter().order_by('-end_date')
        else:
            return Workshop.objects.filter(users=self.request.user).order_by('-end_date')


class WorkshopCreateView(CreateView):
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/form.html'
    success_url = reverse_lazy('workshops-my')

    def form_valid(self, form):
        workshop = form.save(commit=False)
        workshop.save()
        workshop.owner = self.request.user
        workshop.users.add(self.request.user)
        workshop.save()

        return super().form_valid(form)
    
class WorkshopUpdateView(UpdateView):
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/form.html'
    success_url = reverse_lazy('workshops-my')

    def get_object(self, queryset = None):
        workshop = super().get_object(queryset)
        if self.request.user.is_superuser:
            return workshop
        if self.request.user != workshop.owner:
            raise PermissionDenied('You are not allowed to edite this Workshop')
        return workshop

class WorkshopDeleteView(DeleteView):
    model = Workshop
    template_name = 'workshops/confirm_delete.html'
    success_url = reverse_lazy('workshops-my')

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(owner=self.request.user)
        return queryset
    

class WorkshopExportCsvView(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            workshop = Workshop.objects.get(pk=pk)
        except Workshop.DoesNotExist:
            raise Http404("Workshop nicht gefunden.")

        if not workshop.public and workshop.owner != request.user:
            raise Http404("Workshop nicht gefunden.")

        records = AirQualityRecord.objects.filter(workshop__name=pk)

        # CSV-Antwort vorbereiten
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{workshop.name}_data.csv"'

        writer = csv.writer(response)
        header = ['id', 'time', 'pm1', 'pm25', 'pm10', 'temperature', 'humidity', 'device', 'participant', 'lat', 'lon', 'location_precision', 'mode']
        writer.writerow(header)

        for record in records:
            writer.writerow([
                record.id,
                record.time,
                record.pm1,
                record.pm25,
                record.pm10,
                record.temperature,
                record.humidity,
                record.device,
                record.participant,
                record.lat,
                record.lon,
                record.location_precision,
                record.mode
            ])

        return response

class WorkshopImageUploadView(FormView):
    form_class = FileFieldForm
    template_name = "workshops/upload_images.html"  # Replace with your template.

    def get_success_url(self):
        return reverse_lazy('workshop-detail', kwargs={'pk': self.kwargs['workshop_id']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['workshop_id'] = self.kwargs['workshop_id']
        return context

    def form_valid(self, form):
        files = form.cleaned_data["file_field"]

        for img in files:
            success = workshop_add_image(img, workshop_id=self.kwargs['workshop_id'])
            if not success:
                form.add_error('file_field', 'Failed to process one or more images.')
                return self.form_invalid(form)

        return super().form_valid(form)


class WorkshopImportDataView(LoginRequiredMixin, FormView):
    form_class = ImportDataForm
    template_name = 'workshops/import_data.html'

    def get_success_url(self):
        return reverse_lazy('workshop-detail', kwargs={'pk': self.kwargs['workshop_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workshop = get_object_or_404(Workshop, pk=self.kwargs['workshop_id'])
        
        # Check permissions
        if not self.request.user.is_superuser and self.request.user != workshop.owner:
            raise PermissionDenied("You don't have permission to import data for this workshop.")
        
        context['workshop'] = workshop
        context['workshop_id'] = self.kwargs['workshop_id']
        return context

    def form_valid(self, form):
        workshop = get_object_or_404(Workshop, pk=self.kwargs['workshop_id'])
        
        # Check permissions
        if not self.request.user.is_superuser and self.request.user != workshop.owner:
            raise PermissionDenied("You don't have permission to import data for this workshop.")
        
        json_file = form.cleaned_data['json_file']
        
        try:
            # Read and parse JSON file
            file_content = json_file.read().decode('utf-8')
            data = json.loads(file_content)
            
            # Validate JSON structure
            if 'version' not in data or 'device' not in data or 'data' not in data:
                messages.error(self.request, 'Invalid JSON format. Expected version, device, and data fields.')
                return self.form_invalid(form)
            
            # Extract device information
            device_info = data.get('device', {})
            chip_id = device_info.get('chipId', {})
            mac = chip_id.get('mac', '')
            four_letter_code = device_info.get('fourLetterCode', '')
            display_name = device_info.get('displayName', '')
            
            # Create or get device
            # Convert MAC address format: "28372F821AE5" -> reverse byte pairs -> "AAA" suffix
            if mac:
                mac_upper = mac.upper()
                # Reverse byte pairs: "28372F821AE5" -> ["28", "37", "2F", "82", "1A", "E5"] -> reversed -> join
                rmac = ''.join(reversed([mac_upper[i:i+2] for i in range(0, len(mac_upper), 2)]))
                device_id = f'{rmac}AAA'
            else:
                # Fallback: use four letter code if MAC is not available
                device_id = f'{four_letter_code}AAA' if four_letter_code else 'UNKNOWN'
            
            device, _ = Device.objects.get_or_create(id=device_id)
            if display_name and not device.device_name:
                device.device_name = display_name
                device.save()
            
            # Create or get participant (using display name or device name)
            participant_name = display_name or device.device_name or device_id
            participant, _ = Participant.objects.get_or_create(
                name=participant_name,
                defaults={'workshop': workshop}
            )
            if participant.workshop != workshop:
                participant.workshop = workshop
                participant.save()
            
            # Process data points
            data_points = data.get('data', [])
            created_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            for point in data_points:
                try:
                    # Parse timestamp
                    timestamp_str = point.get('timestamp')
                    if not timestamp_str:
                        skipped_count += 1
                        continue
                    
                    # Parse datetime (handle microseconds and timezones)
                    try:
                        time = parse_datetime(timestamp_str)
                        if time is None:
                            # Try parsing with different format
                            if timestamp_str.endswith('Z'):
                                timestamp_str = timestamp_str.replace('Z', '+00:00')
                            time = datetime.fromisoformat(timestamp_str)
                        
                        # Ensure timezone awareness
                        if time.tzinfo is None:
                            time = timezone.make_aware(time)
                    except (ValueError, AttributeError, TypeError) as e:
                        errors.append(f"Invalid timestamp format: {timestamp_str}")
                        error_count += 1
                        continue
                    
                    # Check if time is within workshop timeframe
                    # Allow a 30-day buffer before start and after end to accommodate data collection
                    # This is more lenient for imports since users are explicitly choosing to import the data
                    buffer_before = timedelta(days=30)
                    buffer_after = timedelta(days=30)
                    if not ((workshop.start_date - buffer_before) <= time <= (workshop.end_date + buffer_after)):
                        skipped_count += 1
                        logger.warning(f"Record timestamp {time} is outside workshop timeframe (with buffer: {workshop.start_date - buffer_before} to {workshop.end_date + buffer_after})")
                        continue
                    
                    # Extract location
                    location_data = point.get('location', {})
                    coordinates = location_data.get('coordinates', [])
                    if len(coordinates) != 2:
                        skipped_count += 1
                        continue
                    
                    lon, lat = coordinates[0], coordinates[1]
                    location_precision = location_data.get('precision')
                    
                    # Extract sensor data
                    sensor_data_list = point.get('sensorData', [])
                    if not sensor_data_list:
                        skipped_count += 1
                        continue
                    
                    # Get first sensor data entry (usually only one)
                    sensor_data = sensor_data_list[0] if sensor_data_list else {}
                    
                    # Extract mobility mode
                    mode_name = point.get('mode', 'unknown')
                    mode, _ = MobilityMode.objects.get_or_create(
                        name=mode_name,
                        defaults={'title': mode_name.title(), 'description': ''}
                    )
                    
                    # Check if record already exists
                    if AirQualityRecord.objects.filter(time=time, device=device).exists():
                        skipped_count += 1
                        continue
                    
                    # Map sensor data fields to AirQualityRecord fields
                    # JSON uses: PM1.0, PM2.5, PM4.0, PM10.0, Luftfeuchtigkeit, Temperatur, VOCs
                    # Model uses: pm1, pm25, pm10, humidity, temperature, voc
                    record_data = {
                        'time': time,
                        'pm1': sensor_data.get('PM1.0'),
                        'pm25': sensor_data.get('PM2.5'),
                        'pm10': sensor_data.get('PM10.0'),
                        'humidity': sensor_data.get('Luftfeuchtigkeit'),
                        'temperature': sensor_data.get('Temperatur'),
                        'voc': sensor_data.get('VOCs'),
                        'device': device,
                        'workshop': workshop,
                        'participant': participant,
                        'mode': mode,
                        'lat': lat,
                        'lon': lon,
                        'location_precision': location_precision,
                    }
                    
                    # Create AirQualityRecord
                    record = AirQualityRecord(**record_data)
                    record.save()
                    created_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Error processing data point: {str(e)}")
                    logger.error(f"Error importing data point: {str(e)}", exc_info=True)
            
            # Show success/error messages
            if created_count > 0:
                messages.success(self.request, f'Successfully imported {created_count} records.')
            if skipped_count > 0:
                messages.warning(self.request, f'Skipped {skipped_count} records (duplicates or outside workshop timeframe).')
            if error_count > 0:
                messages.error(self.request, f'Encountered {error_count} errors during import.')
                if errors:
                    logger.error(f"Import errors: {errors}")
            
            return super().form_valid(form)
            
        except json.JSONDecodeError as e:
            messages.error(self.request, f'Invalid JSON file: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error processing file: {str(e)}')
            logger.error(f"Error importing data: {str(e)}", exc_info=True)
            return self.form_invalid(form)
