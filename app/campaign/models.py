from django.db import models
from django.conf import settings
import string
import random

class Campaign(models.Model):
    """
    Represents a campaign.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    public = models.BooleanField(default=True)
    id_token = models.CharField(max_length=8, null=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='campaigns')
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_campaigns',
        null=True,
        blank=True
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='campaigns',
        null = True
    )

    def __str__(self):
        return self.name


class Room(models.Model):
    """
    Represents a room where a campaign takes place.
    """
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('campaign', 'name')

    def __str__(self):
        return f'{self.name} in {self.campaign}'
