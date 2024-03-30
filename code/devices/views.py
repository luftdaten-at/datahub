from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy

from .models import Device
from .forms import DeviceForm

class DeviceListView(UserPassesTestMixin, ListView):
    model = Device
    context_object_name = 'devices'
    template_name = 'devices/devices_list.html'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        # Return the Device queryset ordered by 'name' in ascending order
        return Device.objects.all().order_by('name')


class DeviceDetailView(UserPassesTestMixin, DetailView):
    model = Device
    context_object_name = 'device'
    template_name = 'devices/device_detail.html'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser


class DeviceUpdateView(UpdateView):
    model = Device
    form_class = DeviceForm
    template_name = 'devices/device_form.html'  # Specify your form template
    success_url = reverse_lazy('device-list')  # URL to redirect to after a successful update

    def get_queryset(self):
        """
        Optionally, restrict the queryset to allow editing only for devices
        the user is authorized to edit. This example allows all authenticated
        users to edit any device, but you might want to check user permissions.
        """
        queryset = super().get_queryset()
        return queryset