from django.db import models, transaction
from django.utils import timezone
from organizations.models import Organization
from campaign.models import Room
from accounts.models import CustomUser
from campaign.models import Campaign
from auditlog.registry import auditlog
from auditlog.models import AuditlogHistoryField

from main.enums import LdProduct


class Device(models.Model):
    """
    Device model.
    """
    id = models.CharField(max_length=255, primary_key=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    model = models.IntegerField(null=True, blank=True)
    firmware = models.CharField(max_length=255, blank=True)
    btmac_address = models.CharField(max_length=12, null=True, blank=True)
    last_update = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    api_key = models.CharField(max_length=64, null=True)
    auto_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    current_room = models.ForeignKey(Room, related_name='current_devices', null=True, on_delete=models.SET_NULL, blank=True)
    current_organization = models.ForeignKey(Organization, related_name='current_devices', null=True, on_delete=models.SET_NULL, blank=True)
    current_user = models.ForeignKey(CustomUser, null=True, related_name='current_devices', on_delete=models.SET_NULL, blank=True)
    current_campaign = models.ForeignKey(Campaign, null=True, related_name='current_devices', on_delete=models.SET_NULL, blank=True)

    history = AuditlogHistoryField(pk_indexable=False)

    def save(self, *args, **kwargs):
        # if the model id is not set or the auto_number is already set we don't
        # need to update the auto_number
        if self.model is None:
            super().save(*args, **kwargs)
            return
        
        if self.auto_number:
            # assign name to update existing devices
            # TODO could be removed
            self.device_name = f'{self.get_model_name()} {self.auto_number:04d}'
            super().save(*args, **kwargs)
            return

        # update auto_number for the first time
        with transaction.atomic():
            counter, _ = ModelCounter.objects.get_or_create(model=self.model)
            counter.last_auto_number += 1
            counter.save()

            self.auto_number = counter.last_auto_number
            '''
            assigns a unique name for this device in this format: "{model name}{auto_number}"
            for example "Air Cube 0001"
            '''
            self.device_name = f'{self.get_model_name()} {self.auto_number:04d}'
        
        super().save(*args, **kwargs)
    
    def get_ble_id(self):
        # cuts of the 3 last characters that are use for board identification
        return self.id[:-3]
    
    def get_model_name(self):
        '''returns the corresponding LdProduct name'''
        return LdProduct._names.get(self.model, 'Unknown Model')
    
    def __str__(self):
        return self.id or "Undefined Device"  # Added fallback for undefined IDs
 

class ModelCounter(models.Model):
    model = models.IntegerField(primary_key=True)
    last_auto_number = models.IntegerField(default=0)


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
    sensor_list = models.JSONField(null=True)

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
    time_received = models.DateTimeField(null=True)
    time_measured = models.DateTimeField()
    sensor_model = models.IntegerField()
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='measurements')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, related_name='measurements')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, related_name='measurements')
    workshop = models.ForeignKey('workshops.Workshop', on_delete=models.CASCADE, null=True, related_name='measurements')
    location = models.ForeignKey('api.Location', on_delete=models.CASCADE, null=True, related_name='measurements')
    mode = models.ForeignKey('api.MobilityMode', on_delete=models.CASCADE, null=True, blank=True, related_name='measurements')
    participant = models.ForeignKey('workshops.Participant', on_delete=models.CASCADE, null=True, blank=True, related_name='measurements')

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


auditlog.register(Device)