from django.contrib import admin
from .models import Device, DeviceModel, FirmwareVersion

class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'board_id')

admin.site.register(Device, DeviceAdmin)
admin.site.register(DeviceModel)
admin.site.register(FirmwareVersion)

