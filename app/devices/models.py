from django.db import models
from django.utils import timezone


class Device(models.Model):
    """
    Device model.
    """
    id = models.CharField(max_length=255, primary_key=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    firmware = models.CharField(max_length=12, blank=True)
    btmac_address = models.CharField(max_length=12, null=True, blank=True)
    last_update = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    api_key = models.CharField(max_length=64, null=True)

    def __str__(self):
        return self.id or "Undefined Device"  # Added fallback for undefined IDs
    

class Sensor(models.Model):
    """
    Sensor model.
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)  # Für das Feld "model"
    product_type = models.CharField(max_length=100, blank=True)  # Optionales Feld für "product_type"
    serial = models.CharField(max_length=100, blank=True)  # Für die Seriennummer
    firmware = models.CharField(max_length=50, blank=True)  # Für die Firmware-Version
    hardware = models.CharField(max_length=50, blank=True)  # Für die Hardware-Version
    protocol = models.CharField(max_length=50, blank=True)  # Für die Protokoll-Version

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
