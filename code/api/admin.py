from django.contrib import admin
from .models import AirQualityRecord


class AirQualityRecordAdmin(admin.ModelAdmin):
    list_display = ('time', 'workshop', 'device')

admin.site.register(AirQualityRecord, AirQualityRecordAdmin)