from django.db import models
from workshops.models import Participant, Workshop
from devices.models import Device, Sensor
from campaign.models import Campaign


class MobilityMode(models.Model):
    name = models.CharField(max_length=255, unique=True, primary_key=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    
    def __str__(self):
        return self.name


class AirQualityDatapoint(models.Model):
    """
    Datapoint on one location at a specific time, which can include several measurements.
    """
    time = models.DateTimeField()
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True)
    workshop = models.ForeignKey(Workshop, on_delete=models.SET_NULL, null=True, blank=True)
    participant = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    location_precision = models.FloatField(null=True, blank=True)
    mode = models.ForeignKey(MobilityMode, on_delete=models.SET_NULL, null=True, blank=True)


class Measurement(models.Model):
    """
    Single Measurement with one specific sensor.
    """
    id = models.BigAutoField(unique=True, primary_key=True)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    datapoint = models.ForeignKey(AirQualityDatapoint, on_delete=models.SET_NULL, null=True, blank=True)
    pm1 = models.FloatField(null=True, blank=True, help_text="Particulate matter 1 microns")
    pm25 = models.FloatField(null=True, blank=True, help_text="Particulate matter 2.5 microns")
    pm10 = models.FloatField(null=True, blank=True, help_text="Particulate matter 10 microns")
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    voc_index = models.FloatField(null=True, blank=True, help_text="Volatile organic compound index")
    nox_index = models.FloatField(null=True, blank=True, help_text="Nitrogen oxides index")
    co2 = models.FloatField(null=True, blank=True, help_text="Carbondioxid")
    o3 = models.FloatField(null=True, blank=True, help_text="Ground-level Ozone")
    iaq_index = models.FloatField(null=True, blank=True)
    iaq_acc = models.SmallIntegerField(null=True, blank=True)
    iaq_static = models.FloatField(null=True, blank=True)
    pressure = models.FloatField(null=True, blank=True)


# Old model for air quality storage
# will be removed in one of the following versions
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
    participant = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    location_precision = models.FloatField(null=True, blank=True)
    mode = models.ForeignKey(MobilityMode, on_delete=models.SET_NULL, null=True, blank=True)
