from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import UserPassesTestMixin
from .models import Device

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