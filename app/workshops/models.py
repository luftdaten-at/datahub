from django.db import models
from django.conf import settings
import string
import random

from devices.models import Device
from auditlog.registry import auditlog
from auditlog.models import AuditlogHistoryField

class Workshop(models.Model):
    name = models.CharField(max_length=6, unique=True, primary_key=True, blank=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    public = models.BooleanField(default=True)
    mapbox_top_left_lat = models.FloatField(null=True, blank=True)
    mapbox_top_left_lon = models.FloatField(null=True, blank=True)
    mapbox_top_right_lat = models.FloatField(null=True, blank=True)
    mapbox_top_right_lon = models.FloatField(null=True, blank=True)
    mapbox_bottom_left_lat = models.FloatField(null=True, blank=True)
    mapbox_bottom_left_lon = models.FloatField(null=True, blank=True)
    mapbox_bottom_right_lat = models.FloatField(null=True, blank=True)
    mapbox_bottom_right_lon = models.FloatField(null=True, blank=True)

    history = AuditlogHistoryField()

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_workshops',  # Allows user.owned_workshops.all() to get all owned workshops
        null=True,
        blank=True
    )
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.name:
            # Generate a unique ID for new workshops
            self.name = self.generate_name()
        super(Workshop, self).save(*args, **kwargs)

    @staticmethod
    def generate_name():
        length = 6
        # Generate a random string of letters and digits
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        
        # Ensure the generated ID is unique
        while Workshop.objects.filter(name=name).exists():
            name = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        return name
    
class Participant(models.Model):
    name = models.CharField(max_length=255, unique=True, primary_key=True, blank=True)
    workshop = models.ForeignKey(Workshop, on_delete=models.SET_NULL, null=True)
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True)

    history = AuditlogHistoryField()

    def __str__(self):
        return self.name

auditlog.register(Workshop) 
auditlog.register(Participant)