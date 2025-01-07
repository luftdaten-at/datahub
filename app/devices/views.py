from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator
import json

from .models import Device, DeviceStatus, DeviceLogs
from .forms import DeviceForm, DeviceNotesForm

class DeviceListView(UserPassesTestMixin, ListView):
    model = Device
    context_object_name = 'devices'
    template_name = 'devices/list.html'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        # Return the Device queryset ordered by 'id' in ascending order
        return Device.objects.all().order_by('id')


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
        device_status_qs = DeviceStatus.objects.filter(device=device).order_by('time_received')
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
            10: 'bg-secondary',  # DEBUG
            20: 'bg-info',        # INFO
            30: 'bg-warning',     # WARNING
            40: 'bg-danger',      # ERROR
            50: 'bg-dark',        # CRITICAL
        }

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
        Define the condition that the user must meet to access this view.
        For example, only superusers can edit notes.
        Adjust this logic based on your application's requirements.
        """
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        """
        Restrict the queryset to devices the user is allowed to edit.
        For example, if users can only edit their own devices, filter accordingly.
        Adjust the filter based on your application's logic.
        """
        return Device.objects.all()  # Modify as per your permission logic


from django.db import transaction

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

