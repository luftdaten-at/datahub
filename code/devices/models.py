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
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=4)
    model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE, null=True)
    board_id = models.CharField(max_length=12, null=True, blank=True, unique=True)
    btmac_address = models.CharField(max_length=12, null=True, blank=True)
    sensor_sen5x = models.CharField(max_length = 255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.board_id
    

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
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    time_received = models.DateTimeField()
    status = models.JSONField()

    def save(self, *args, **kwargs):
        if not self.pk:  # Check if the instance is new
            self.time_received = timezone.now()  # Set the created_at field only if it's a new instance
        super(DeviceStatus, self).save(*args, **kwargs)


