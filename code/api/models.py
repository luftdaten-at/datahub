from django.db import models
from workshops.models import Participant, Workshop
from devices.models import Device


class MobilityMode(models.Model):
    name = models.CharField(max_length=255, unique=True, primary_key=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    
    def __str__(self):
        return self.name

class AirQualityRecord(models.Model):
    time = models.DateTimeField()
    pm1 = models.FloatField(null=True, blank=True)
    pm25 = models.FloatField(null=True, blank=True)
    pm10 = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    voc = models.FloatField(null=True, blank=True)
    nox = models.FloatField(null=True, blank=True)
    co2 = models.FloatField(null=True, blank=True)
    o3 = models.FloatField(null=True, blank=True)
    iaq_index = models.FloatField(null=True, blank=True)
    iaq_acc = models.SmallIntegerField(null=True, blank=True)
    iaq_static = models.FloatField(null=True, blank=True)
    pressure = models.FloatField(null=True, blank=True)
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True)
    workshop = models.ForeignKey(Workshop, on_delete=models.SET_NULL, null=True, blank=True)
    participant = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    location_precision = models.FloatField(null=True, blank=True)
    mode = models.ForeignKey(MobilityMode, on_delete=models.SET_NULL, null=True, blank=True)

