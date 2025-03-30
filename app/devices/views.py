import json
from collections import defaultdict
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext as _
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator
from django.db import transaction

from .models import Device, DeviceStatus, DeviceLogs, Measurement
from accounts.models import CustomUser
from .forms import DeviceForm, DeviceNotesForm
from main.enums import SensorModel, Dimension
from organizations.models import Organization
from campaign.models import Room

class DeviceListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Device
    context_object_name = 'devices'
    template_name = 'devices/list.html'

    def test_func(self):
        # Only superusers can access this view
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        # Optimize queryset by selecting related 'current_organization'
        return Device.objects.select_related('current_organization').all().order_by('id')

class DeviceDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Device
    context_object_name = 'device'
    template_name = 'devices/detail.html'

    def test_func(self):
        # Only superusers can access this view
        return self.request.user.is_authenticated and self.request.user.is_superuser

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
            # Prepare data for Chart.js
            battery_times = [
                status.time_received.strftime('%Y-%m-%d %H:%M') 
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

            # query changes
            organization_changes = device.history.filter(changes__icontains = '"current_organization"').all().order_by('-timestamp')
            room_changes = device.history.filter(changes__icontains = '"current_room"').all().order_by('-timestamp')
            user_changes = device.history.filter(changes__icontains = '"current_user"').all().order_by('-timestamp')
            
            organization_change_log = []
            room_change_log = []
            user_change_log = []

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

            context['organization_change_log'] = organization_change_log 
            context['room_change_log'] = room_change_log
            context['user_change_log'] = user_change_log
            
            # Serialize data to JSON format
            context['battery_times'] = json.dumps(battery_times, cls=DjangoJSONEncoder)
            context['battery_charges'] = json.dumps(battery_charges, cls=DjangoJSONEncoder)
            context['battery_voltages'] = json.dumps(battery_voltages, cls=DjangoJSONEncoder)

        # Fetch all DeviceLogs entries related to this Device, ordered by timestamp descendingly
        device_logs_qs = DeviceLogs.objects.filter(device=device).order_by('-timestamp')
        
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


class DeviceMyView(UserPassesTestMixin, ListView):
    model = Device
    context_object_name = 'device'
    template_name = 'devices/my.html'

    def test_func(self):
        return self.request.user.is_authenticated 

    def get_queryset(self):
        # Return the Device queryset ordered by 'id' in ascending order
        return Device.objects.all().order_by('id')


class DeviceEditView(UpdateView):
    model = Device
    form_class = DeviceForm
    template_name = 'devices/form.html'
    success_url = reverse_lazy('device-list')  # URL to redirect to after a successful update

    def get_queryset(self):
        """
        Optionally, restrict the queryset to allow editing only for devices
        the user is authorized to edit. This example allows all authenticated
        users to edit any device, but you might want to check user permissions.
        """
        queryset = super().get_queryset()
        return queryset


class DeviceNotesUpdateView(LoginRequiredMixin, UpdateView):
    model = Device
    form_class = DeviceNotesForm
    template_name = 'devices/edit_notes.html'

    def get_success_url(self):
        """
        After successfully updating the notes, redirect to the device's detail page.
        """
        return reverse('device-detail', kwargs={'pk': self.object.pk})
    
    def test_func(self):
        """
        Only superusers can edit notes.
        """
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        """
        Restrict the queryset to devices the user is allowed to edit.
        For example, if users can only edit their own devices, filter accordingly.
        Adjust the filter based on your application's logic.
        """
        return Device.objects.all()
    

class DeviceDeleteView(LoginRequiredMixin, DeleteView):
    model = Device
    template_name = 'devices/confirm_delete.html'  # Confirmation page template
    success_url = reverse_lazy('device-list')  # Redirect here after deletion

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

