from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from .models import Device


class DeviceListView(ListView):
    model = Device
    context_object_name = 'devices'
    template_name = 'devices/devices_list.html'

    def get_queryset(self):
        # Return the Device queryset ordered by 'name' in ascending order
        return Device.objects.all().order_by('name')


class DeviceDetailView(DetailView):
    model = Device
    context_object_name = 'device'
    template_name = 'devices/device_detail.html'