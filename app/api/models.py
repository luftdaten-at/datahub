from django.db import models
from workshops.models import Participant, Workshop
from devices.models import Device, Sensor
from django.contrib.gis.db.models import PointField
#from campaign.models import Campaign


class MobilityMode(models.Model):
    name = models.CharField(max_length=255, unique=True, primary_key=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    
    def __str__(self):
        return self.name


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
    device = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, related_name='air_quality_records')
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, null=True, blank=True, related_name='air_quality_records')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    location_precision = models.FloatField(null=True, blank=True)
    mode = models.ForeignKey(MobilityMode, on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey('api.Location', on_delete=models.CASCADE, null=True, related_name='air_quality_records')

    def save(self, *args, **kwargs):
        if self.lat is not None and self.lon is not None and not self.location:
            from django.contrib.gis.geos import Point
            Location = self._meta.get_field('location').related_model
            point = Point(self.lon, self.lat, srid=4326)
            location_obj = Location.objects.create(coordinates=point)
            self.location = location_obj
        super().save(*args, **kwargs)


class Location(models.Model):
    coordinates = PointField()
    height = models.FloatField(null=True)
