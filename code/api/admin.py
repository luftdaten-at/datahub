from django.contrib import admin
from .models import AirQualityRecord, Location

admin.site.register(AirQualityRecord)
admin.site.register(Location)