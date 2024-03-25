from django.contrib import admin
from .models import AirQualityRecord, MobilityMode


class MobilityModeAdmin(admin.ModelAdmin):
    list_display = ('title', 'name')

admin.site.register(MobilityMode, MobilityModeAdmin)


class AirQualityRecordAdmin(admin.ModelAdmin):
    list_display = ('time', 'workshop', 'device')

admin.site.register(AirQualityRecord, AirQualityRecordAdmin)