from django.db import models
from workshops.models import Workshop
from devices.models import Device


class AirQualityRecord(models.Model):
    time = models.DateTimeField()
    pm1 = models.IntegerField(null=True, blank=True)
    pm25 = models.IntegerField(null=True, blank=True)
    pm10 = models.IntegerField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.IntegerField(null=True, blank=True)
    voc = models.IntegerField(null=True, blank=True)
    nox = models.IntegerField(null=True, blank=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, null=True)
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, null=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    location_precision = models.IntegerField(null=True, blank=True)