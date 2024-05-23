from django.db import models
from django.utils import timezone


class DeviceModel(models.Model):
    """
    Device model model.
    """
    name = models.CharField(max_length=255, unique=True, primary_key=True)
    description = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.name


class Device(models.Model):
    """
    Device model.
    """
    id = models.CharField(max_length=12, primary_key=True, blank=True)
    device_name = models.CharField(max_length=255, null=True, blank=True)
    model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE, null=True)
    btmac_address = models.CharField(max_length=12, null=True, blank=True)
    sensor_sen5x = models.CharField(max_length = 255, null=True, blank=True)
    sensor_bme280 = models.CharField(max_length = 255, null=True, blank=True)
    sensor_bme680 = models.CharField(max_length = 255, null=True, blank=True)
    last_update = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.id or "Undefined Device"  # Added fallback for undefined IDs
    

class Sensor(models.Model):
    """
    Sensor model.
    """
    name = models.CharField(max_length=255, unique=True, primary_key=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    

class DeviceStatus(models.Model):
    """
    Device status model.
    """
    id = models.BigAutoField(primary_key=True)
    time_received = models.DateTimeField()
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    battery_voltage = models.FloatField(null=True, blank=True)
    battery_soc = models.FloatField(null=True, blank=True)
    sensors = models.JSONField()

    def save(self, *args, **kwargs):
        if not self.pk:  # Check if the instance is new
            self.time_received = timezone.now()  # Set the created_at field only if it's a new instance
        super(DeviceStatus, self).save(*args, **kwargs)

    def __str__(self):
        return f"Status at {self.time_received}"
