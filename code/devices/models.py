from django.db import models

class FirmwareVersion(models.Model):
    """
    Firmware version model.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

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
    firmware_version = models.ForeignKey(FirmwareVersion, on_delete=models.CASCADE, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name