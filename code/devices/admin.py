from django.contrib import admin
from .models import Device, DeviceModel, FirmwareVersion

admin.site.register(Device)
admin.site.register(DeviceModel)
admin.site.register(FirmwareVersion)