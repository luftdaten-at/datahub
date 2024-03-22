from django.db import models


class DeviceModel(models.Model):
    name = models.CharField(max_length=255, unique=True, primary_key=True)
    
    def __str__(self):
        return self.name


class Device(models.Model):
    name = models.CharField(max_length=4, unique=True, primary_key=True)
    model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE, null=True)
    board_id = models.CharField(max_length=12, null=True, blank=True)
    btmac_address = models.CharField(max_length=12, null=True, blank=True)
    sensor_sen5x = models.CharField(max_length = 255, null=True, blank=True)

    def __str__(self):
        return self.name