from django.db import models
from django.utils import timezone
from campaign.models import Room, Organization


class Device(models.Model):
    """
    Device model.
    """
    id = models.CharField(max_length=255, primary_key=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    firmware = models.CharField(max_length=255, blank=True)
    btmac_address = models.CharField(max_length=12, null=True, blank=True)
    last_update = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    api_key = models.CharField(max_length=64, null=True)
    current_room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='current_devices', null=True)
    current_organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='current_devices', null=True)

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
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='status_list')
    battery_voltage = models.FloatField(null=True, blank=True)
    battery_soc = models.FloatField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:  # Check if the instance is new
            self.time_received = timezone.now()  # Set the created_at field only if it's a new instance
        super(DeviceStatus, self).save(*args, **kwargs)

    def __str__(self):
        return f"Status at {self.time_received}"


class DeviceLogs(models.Model):
    """
    Logs for each device.
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    level = models.IntegerField()
    message = models.TextField()

    def __str__(self):
        return f'Log {self.id} for Device {self.device.id}'


class Measurement(models.Model):
    """
    Measurement taken by a device in a room.
    """
    time_received = models.DateTimeField()
    time_measured = models.DateTimeField()
    sensor_model = models.IntegerField()
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='measurements')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, related_name='measurements')

    def __str__(self):
        return f'Measurement {self.id} from Device {self.device.id}'


class Values(models.Model):
    """
    Values associated with a measurement.
    """
    dimension = models.IntegerField()
    value = models.FloatField()
    measurement = models.ForeignKey(Measurement, on_delete=models.CASCADE, related_name='values')

    def __str__(self):
        return f'Value {self.id} for Measurement {self.measurement.id}'
