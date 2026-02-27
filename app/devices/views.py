import json
import logging
from collections import defaultdict
import csv
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext as _
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib import messages

from .models import Device, DeviceStatus, DeviceLogs, Measurement, Values
from accounts.models import CustomUser
from .forms import DeviceForm, DeviceNotesForm, DeviceApikeyForm
from main.enums import SensorModel, Dimension, LdProduct
from organizations.models import Organization
from campaign.models import Room
from workshops.models import Workshop
from api.models import AirQualityRecord
from django.db.models import Count, Min, Max, Q, OuterRef, Subquery
from django.db.models.functions import Length


logger = logging.getLogger('myapp')

class DeviceListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Device
    context_object_name = 'devices'
    template_name = 'devices/list.html'

    def test_func(self):
        # Only superusers can access this view
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        # Optimize queryset by selecting related 'current_organization'
        device_list = Device.objects.select_related('current_organization').all().order_by('id')
        device_list = [device for device in device_list if len(device.id) >= 15]

        return device_list


class AirStationsOverviewView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin-only overview of Air Stations with last status and last send data."""
    model = Device
    context_object_name = 'air_stations'
    template_name = 'devices/air_stations_overview.html'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        latest_log = DeviceLogs.objects.filter(device=OuterRef('pk')).order_by('-timestamp')
        return (
            Device.objects.filter(model=LdProduct.AIR_STATION)
            .annotate(id_len=Length('id'))
            .filter(id_len__gte=15)
            .select_related('current_organization')
            .annotate(
                last_log_time=Subquery(latest_log.values('timestamp')[:1]),
                last_log_message=Subquery(latest_log.values('message')[:1]),
                last_measurement_time=Max('measurements__time_measured'),
                last_aqr_time=Max('air_quality_records__time'),
            )
            .order_by('id')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Compute last_send_data for each device (max of measurement and aqr times)
        for device in context['air_stations']:
            times = [t for t in (device.last_measurement_time, device.last_aqr_time) if t is not None]
            device.last_send_data = max(times) if times else None
        return context


class DeviceDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Device
    context_object_name = 'device'
    template_name = 'devices/detail.html'

    def test_func(self):
        # Only superusers can access this view
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return TemplateResponse(
                self.request,
                'devices/detail_logs_partial.html',
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.object

        # Fetch all DeviceStatus entries related to this Device, ordered by time_received ascendingly
        device_status_qs = DeviceStatus.objects.filter(
            device=device,
            battery_soc__isnull=False
        ).order_by('time_received')
        context['battery_status'] = device_status_qs.exists()

        if context['battery_status']:
            # Prepare data for Chart.js (two-line labels: date on first line, time on second)
            battery_times = [
                [
                    status.time_received.strftime('%Y-%m-%d'),
                    status.time_received.strftime('%H:%M')
                ]
                for status in device_status_qs
                if status.battery_soc is not None and status.battery_voltage is not None
            ]
            battery_charges = [
                min(max(status.battery_soc, 0), 100) 
                for status in device_status_qs 
                if status.battery_soc is not None and status.battery_voltage is not None
            ]
            battery_voltages = [
                round(status.battery_voltage, 2) 
                for status in device_status_qs 
                if status.battery_soc is not None and status.battery_voltage is not None
            ]            
            # Serialize data to JSON format
            context['battery_times'] = json.dumps(battery_times, cls=DjangoJSONEncoder)
            context['battery_charges'] = json.dumps(battery_charges, cls=DjangoJSONEncoder)
            context['battery_voltages'] = json.dumps(battery_voltages, cls=DjangoJSONEncoder)
        
        # query changes
        organization_changes = device.history.filter(changes__icontains = '"current_organization"').all().order_by('-timestamp')
        room_changes = device.history.filter(changes__icontains = '"current_room"').all().order_by('-timestamp')
        user_changes = device.history.filter(changes__icontains = '"current_user"').all().order_by('-timestamp')
        
        organization_change_log = []
        room_change_log = []
        user_change_log = []
        workshop_change_log = []

        # prepare changes
        for h in organization_changes:
            prev = h.changes['current_organization'][0]
            next = h.changes['current_organization'][1]
            organization_change_log.append({
                'timestamp': h.timestamp,
                'prev': None if prev == 'None' else Organization.objects.filter(id=prev).first(),
                'next': None if next == 'None' else Organization.objects.filter(id=next).first(),
            })
        for h in room_changes:
            prev = h.changes['current_room'][0]
            next = h.changes['current_room'][1]
            room_change_log.append({
                'timestamp': h.timestamp,
                'prev': None if prev == 'None' else Room.objects.filter(id=prev).first(),
                'next': None if next == 'None' else Room.objects.filter(id=next).first(),
            })
        for h in user_changes:
            prev = h.changes['current_user'][0]
            next = h.changes['current_user'][1]
            user_change_log.append({
                'timestamp': h.timestamp,
                'prev': None if prev == 'None' else CustomUser.objects.filter(id=prev).first(),
                'next': None if next == 'None' else CustomUser.objects.filter(id=next).first(),
            })
        
        # time, workshop
        workshop_changes = []
        for record in reversed(sorted((record.time_measured, record.workshop.name) for record in device.measurements.all() if record.workshop is not None)):
            if not workshop_changes or workshop_changes[-1][1] != record[1]:
                workshop_changes.append(record)

        for i in range(0, len(workshop_changes)):
            workshop_change_log.append({
                'timestamp': workshop_changes[i][0],
                'prev': None if i == len(workshop_changes) - 1 else workshop_changes[i + 1][1],
                'next': workshop_changes[i][1]
            })

        current_workshop = workshop_change_log[0]['next'] if workshop_change_log else None

        context['organization_change_log'] = organization_change_log 
        context['room_change_log'] = room_change_log
        context['user_change_log'] = user_change_log
        context['workshop_change_log'] = workshop_change_log
        context['current_workshop'] = current_workshop

        # Fetch all DeviceLogs entries related to this Device, ordered by timestamp descendingly
        device_logs_qs = DeviceLogs.objects.filter(device=device).order_by('-timestamp')

        # Apply search filter
        search_q = self.request.GET.get('q', '').strip()
        if search_q:
            device_logs_qs = device_logs_qs.filter(message__icontains=search_q)

        context['status_log_search'] = search_q

        # Implement pagination (10 logs per page)
        paginator = Paginator(device_logs_qs, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['device_logs'] = page_obj
        context['paginator'] = paginator
        context['page_obj'] = page_obj

        # Define a level to badge class mapping
        context['level_badge_map'] = {
            0: 'bg-secondary',  # DEBUG
            1: 'bg-info',        # INFO
            2: 'bg-warning',     # WARNING
            3: 'bg-danger',      # ERROR
            4: 'bg-dark',        # CRITICAL
        }

        context['level_map'] = {
            0: 'debug',
            1: 'info',
            2: 'warning',
            3: 'error',
            4: 'critical',
        }

        sensors = defaultdict(list)
        # add available sensors
        q = Measurement.objects.filter(device=device, time_measured=device.last_update).all()
        if not q:
            try:
                status = device.status_list.filter(sensor_list__isnull=False).latest('time_received')
            except DeviceStatus.DoesNotExist:
                status = None
            if status:
                for data in status.sensor_list:
                    sensors[SensorModel.get_sensor_name(data['model_id'])].extend(Dimension.get_name(dim) for dim in data['dimension_list'])
        else:
            for measurement in q:
                for value in measurement.values.all():
                    sensors[SensorModel.get_sensor_name(measurement.sensor_model)].append(Dimension.get_name(value.dimension))

        context['sensors'] = dict(sensors)

        return context


class DeviceDataView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View to show all workshops and data collected for a device."""
    model = Device
    context_object_name = 'device'
    template_name = 'devices/data.html'
    pk_url_kwarg = 'pk'

    def test_func(self):
        # Only superusers can access this view
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.object

        # Get all workshops that have measurements for this device (from Measurement model)
        workshops_from_measurements = Workshop.objects.filter(
            measurements__device=device
        ).distinct().annotate(
            measurement_count=Count('measurements', filter=Q(measurements__device=device)),
            first_measurement=Min('measurements__time_measured', filter=Q(measurements__device=device)),
            last_measurement=Max('measurements__time_measured', filter=Q(measurements__device=device))
        )

        # Get all workshops that have air quality records for this device (from AirQualityRecord model)
        workshops_from_aqr = Workshop.objects.filter(
            air_quality_records__device=device
        ).distinct().annotate(
            aqr_count=Count('air_quality_records', filter=Q(air_quality_records__device=device)),
            first_aqr=Min('air_quality_records__time', filter=Q(air_quality_records__device=device)),
            last_aqr=Max('air_quality_records__time', filter=Q(air_quality_records__device=device))
        )

        # Combine both querysets and get unique workshops
        all_workshop_ids = set()
        workshop_dict = {}
        
        # Process Measurement-based workshops
        for workshop in workshops_from_measurements:
            all_workshop_ids.add(workshop.pk)
            workshop_dict[workshop.pk] = {
                'workshop': workshop,
                'measurement_count': workshop.measurement_count or 0,
                'aqr_count': 0,
                'first_measurement': workshop.first_measurement,
                'last_measurement': workshop.last_measurement,
                'first_aqr': None,
                'last_aqr': None,
            }
        
        # Process AirQualityRecord-based workshops
        for workshop in workshops_from_aqr:
            all_workshop_ids.add(workshop.pk)
            if workshop.pk in workshop_dict:
                # Update existing entry
                workshop_dict[workshop.pk]['aqr_count'] = workshop.aqr_count or 0
                workshop_dict[workshop.pk]['first_aqr'] = workshop.first_aqr
                workshop_dict[workshop.pk]['last_aqr'] = workshop.last_aqr
            else:
                # Create new entry
                workshop_dict[workshop.pk] = {
                    'workshop': workshop,
                    'measurement_count': 0,
                    'aqr_count': workshop.aqr_count or 0,
                    'first_measurement': None,
                    'last_measurement': None,
                    'first_aqr': workshop.first_aqr,
                    'last_aqr': workshop.last_aqr,
                }

        # Prepare workshop data with additional statistics
        workshop_data = []
        for workshop_id in all_workshop_ids:
            data = workshop_dict[workshop_id]
            workshop = data['workshop']
            
            # Get unique sensors and dimensions from Measurement model
            measurements = Measurement.objects.filter(
                device=device,
                workshop=workshop
            ).select_related().prefetch_related('values')

            sensors_used = set()
            dimensions_used = set()
            for measurement in measurements:
                sensors_used.add(measurement.sensor_model)
                for value in measurement.values.all():
                    dimensions_used.add(value.dimension)

            # Get dimensions from AirQualityRecord (they have pm1, pm25, pm10, temperature, humidity, etc.)
            aqr_records = AirQualityRecord.objects.filter(device=device, workshop=workshop)
            if aqr_records.exists():
                # Add common dimensions from AQR
                if aqr_records.filter(pm1__isnull=False).exists():
                    dimensions_used.add(Dimension.PM1_0)
                if aqr_records.filter(pm25__isnull=False).exists():
                    dimensions_used.add(Dimension.PM2_5)
                if aqr_records.filter(pm10__isnull=False).exists():
                    dimensions_used.add(Dimension.PM10_0)
                if aqr_records.filter(temperature__isnull=False).exists():
                    dimensions_used.add(Dimension.TEMPERATURE)
                if aqr_records.filter(humidity__isnull=False).exists():
                    dimensions_used.add(Dimension.HUMIDITY)
                if aqr_records.filter(voc__isnull=False).exists():
                    dimensions_used.add(Dimension.VOC_INDEX)
                if aqr_records.filter(nox__isnull=False).exists():
                    dimensions_used.add(Dimension.NOX_INDEX)
                if aqr_records.filter(co2__isnull=False).exists():
                    dimensions_used.add(Dimension.CO2)
                if aqr_records.filter(o3__isnull=False).exists():
                    dimensions_used.add(Dimension.O3)
                if aqr_records.filter(pressure__isnull=False).exists():
                    dimensions_used.add(Dimension.PRESSURE)

            # Convert to readable names
            sensor_names = [SensorModel.get_sensor_name(s) for s in sensors_used]
            dimension_names = [Dimension.get_name(d) for d in dimensions_used]

            # Determine earliest and latest timestamps
            first_time = None
            last_time = None
            if data['first_measurement'] and data['first_aqr']:
                first_time = min(data['first_measurement'], data['first_aqr'])
            elif data['first_measurement']:
                first_time = data['first_measurement']
            elif data['first_aqr']:
                first_time = data['first_aqr']
                
            if data['last_measurement'] and data['last_aqr']:
                last_time = max(data['last_measurement'], data['last_aqr'])
            elif data['last_measurement']:
                last_time = data['last_measurement']
            elif data['last_aqr']:
                last_time = data['last_aqr']

            total_count = data['measurement_count'] + data['aqr_count']

            workshop_data.append({
                'workshop': workshop,
                'measurement_count': total_count,
                'measurement_count_new': data['measurement_count'],
                'aqr_count': data['aqr_count'],
                'first_measurement': first_time,
                'last_measurement': last_time,
                'sensors': sorted(sensor_names),
                'dimensions': sorted(dimension_names),
            })

        # Sort by first measurement time (most recent first)
        from datetime import datetime
        workshop_data.sort(key=lambda x: x['first_measurement'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        context['workshop_data'] = workshop_data
        context['total_measurements'] = Measurement.objects.filter(device=device).count() + AirQualityRecord.objects.filter(device=device).count()
        context['total_workshops'] = len(workshop_data)

        return context


class DeviceMeasurementsView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View to show a paginated table of all measurements for a device."""
    model = Device
    context_object_name = 'device'
    template_name = 'devices/measurements.html'
    pk_url_kwarg = 'pk'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.object

        # Parse filter params
        filter_workshop = self.request.GET.get('workshop')
        filter_participant = self.request.GET.get('participant')
        filter_sensor = self.request.GET.get('sensor')

        measurements_qs = (
            Measurement.objects.filter(device=device)
            .select_related('workshop', 'participant', 'mode', 'location')
            .prefetch_related('values')
            .order_by('-time_measured')
        )

        # Apply filters
        if filter_workshop:
            measurements_qs = measurements_qs.filter(workshop__pk=filter_workshop)
        if filter_participant:
            measurements_qs = measurements_qs.filter(participant__name=filter_participant)
        filter_sensor_id = None
        if filter_sensor:
            try:
                filter_sensor_id = int(filter_sensor)
                measurements_qs = measurements_qs.filter(sensor_model=filter_sensor_id)
            except (ValueError, TypeError):
                pass

        # Build filter options from unfiltered base
        base_qs = Measurement.objects.filter(device=device)
        workshops = list(
            Workshop.objects.filter(measurements__device=device)
            .distinct().order_by('name')
            .values_list('pk', 'title')
        )
        participants = list(
            base_qs.exclude(participant__isnull=True)
            .values_list('participant__name', flat=True).distinct()
        )
        sensor_ids = list(base_qs.values_list('sensor_model', flat=True).distinct())
        sensors = [(sid, SensorModel.get_sensor_name(sid)) for sid in sorted(sensor_ids)]

        # Get dimensions (from filtered set for correct columns)
        all_dim_ids = set(
            Values.objects.filter(measurement__in=measurements_qs)
            .values_list('dimension', flat=True)
            .distinct()
        )
        if not all_dim_ids:
            all_dim_ids = set(
                Values.objects.filter(measurement__device=device)
                .values_list('dimension', flat=True)
                .distinct()
            )
        dimension_names = {d: Dimension.get_name(d) for d in all_dim_ids}
        common_dims = [
            Dimension.PM1_0, Dimension.PM2_5, Dimension.PM10_0,
            Dimension.TEMPERATURE, Dimension.HUMIDITY,
            Dimension.VOC_INDEX, Dimension.NOX_INDEX, Dimension.PRESSURE,
            Dimension.CO2, Dimension.PM0_1, Dimension.PM4_0,
        ]
        dimension_columns = [d for d in common_dims if d in dimension_names] + sorted(all_dim_ids - set(common_dims))

        paginator = Paginator(measurements_qs, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        measurements = page_obj.object_list

        table_rows = []
        for m in measurements:
            values_dict = {v.dimension: (v.value, Dimension.get_unit(v.dimension)) for v in m.values.all()}
            table_rows.append({
                'measurement': m,
                'values': values_dict,
                'sensor_name': SensorModel.get_sensor_name(m.sensor_model),
            })

        # Build query string for pagination (preserve filters)
        filter_params = []
        if filter_workshop:
            filter_params.append(f'workshop={filter_workshop}')
        if filter_participant:
            filter_params.append(f'participant={filter_participant}')
        if filter_sensor:
            filter_params.append(f'sensor={filter_sensor}')
        filter_query = '&'.join(filter_params)

        context['page_obj'] = page_obj
        context['measurements'] = measurements
        context['table_rows'] = table_rows
        context['dimension_columns'] = dimension_columns
        context['dimension_names'] = dimension_names
        context['total_count'] = paginator.count
        context['filter_workshop'] = filter_workshop
        context['filter_participant'] = filter_participant
        context['filter_sensor'] = filter_sensor
        context['filter_sensor_id'] = filter_sensor_id
        context['filter_query'] = filter_query
        context['filter_options'] = {
            'workshops': workshops,
            'participants': participants,
            'sensors': sensors,
        }

        return context


class MeasurementDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Delete a measurement. Requires superuser. Redirects back to measurements list."""
    http_method_names = ['post']

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def post(self, request, pk, measurement_pk):
        device = get_object_or_404(Device, pk=pk)
        measurement = get_object_or_404(Measurement, pk=measurement_pk, device=device)
        measurement.delete()
        messages.success(request, _('Measurement deleted.'))
        next_url = request.POST.get('next') or reverse('device-measurements', kwargs={'pk': device.pk})
        return HttpResponseRedirect(next_url)


class DeviceMyView(UserPassesTestMixin, ListView):
    model = Device
    context_object_name = 'device'
    template_name = 'devices/my.html'

    def test_func(self):
        return self.request.user.is_authenticated

    def get_queryset(self):
        return Device.objects.all().order_by('id')


class DeviceEditView(UpdateView):
    model = Device
    form_class = DeviceForm
    template_name = 'devices/form.html'
    success_url = reverse_lazy('devices-list')  # URL to redirect to after a successful update

    def get_queryset(self):
        """
        Optionally, restrict the queryset to allow editing only for devices
        the user is authorized to edit. This example allows all authenticated
        users to edit any device, but you might want to check user permissions.
        """
        queryset = super().get_queryset()
        return queryset


class DeviceNotesUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Device
    form_class = DeviceNotesForm
    template_name = 'devices/edit_notes.html'

    def get_success_url(self):
        """
        After successfully updating the notes, redirect to the device's detail page.
        """
        return reverse('device-detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        """
        Restrict the queryset to devices the user is allowed to edit.
        For example, if users can only edit their own devices, filter accordingly.
        Adjust the filter based on your application's logic.
        """
        return Device.objects.all()


class DeviceApikeyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Device
    form_class = DeviceApikeyForm
    template_name = 'devices/edit_apikey.html'

    def get_success_url(self):
        return reverse('device-detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        return Device.objects.all()


class DeviceDeleteView(LoginRequiredMixin, DeleteView):
    model = Device
    template_name = 'devices/confirm_delete.html'  # Confirmation page template
    success_url = reverse_lazy('devices-list')  # Redirect here after deletion

    def get_object(self, queryset = None):
        device = super().get_object(queryset)
        user = self.request.user
        
        if user.is_superuser:
            return device
        else:
            raise PermissionDenied(_('You are not allowed to delete this device.'))

def change_device_id(old_id, new_id):
    try:
        with transaction.atomic():  # Ensures the operation is atomic
            # Retrieve the device with the old ID
            device = Device.objects.get(id=old_id)
            # Change the ID to the new value
            device.id = new_id
            device.save()
    except Device.DoesNotExist:
        print("Device with the specified ID does not exist")
    except Exception as e:
        print(f"An error occurred: {e}")


# View to export DeviceLogs for a given Device as CSV
class DeviceLogsCSVView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View to export DeviceLogs for a given Device as CSV.
    """
    def test_func(self):
        # Only superusers may export logs
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get(self, request, pk, *args, **kwargs):
        # Fetch the device or return 404
        device = get_object_or_404(Device, pk=pk)
        # Query all logs for this device, ordered by timestamp descending
        logs = DeviceLogs.objects.filter(device=device).order_by('-timestamp')

        # Prepare HTTP response with CSV content
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="device_{device.id}_logs.csv"'

        writer = csv.writer(response)
        # Write header
        writer.writerow(['timestamp', 'level', 'message'])
        # Write log rows
        for log in logs:
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.level,
                log.message
            ])

        return response


def calibrationView(request):
    context = {} 
    return render(request=request, template_name='devices/calibration.html', context=context)
