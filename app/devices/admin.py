from django.contrib import admin
from .models import Device, DeviceStatus

class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'device_name', 'model', 'last_update')

class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'device', 'time_received')

admin.site.register(Device, DeviceAdmin)
admin.site.register(DeviceStatus)
