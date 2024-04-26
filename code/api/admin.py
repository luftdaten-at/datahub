from django.contrib import admin
from .models import AirQualityRecord, MobilityMode

import csv
from django.http import HttpResponse

def export_as_csv(modeladmin, request, queryset):
    """
    Export AirQualityRecords as CSV function for the backend
    """
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="air_quality_records.csv"'

    writer = csv.writer(response)
    fields = [field for field in AirQualityRecord._meta.fields]
    writer.writerow([field.verbose_name for field in fields])  # column headers

    for obj in queryset:
        row = []
        for field in fields:
            value = getattr(obj, field.name)
            if callable(value):
                value = value()
            row.append(value)
        writer.writerow(row)

    return response

export_as_csv.short_description = "Export Selected to CSV"


class MobilityModeAdmin(admin.ModelAdmin):
    list_display = ('title', 'name')

admin.site.register(MobilityMode, MobilityModeAdmin)


class AirQualityRecordAdmin(admin.ModelAdmin):
    list_display = ('time', 'workshop', 'device')
    actions = [export_as_csv]

admin.site.register(AirQualityRecord, AirQualityRecordAdmin)