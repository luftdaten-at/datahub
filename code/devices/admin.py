from django.contrib import admin
from .models import Device, DeviceModel, DeviceStatus

class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'device_name')

class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'device', 'time_received')

admin.site.register(Device, DeviceAdmin)
admin.site.register(DeviceModel)
admin.site.register(DeviceStatus)
