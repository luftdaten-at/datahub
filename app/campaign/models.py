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
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_campaigns',
        null=True,
        blank=True
    )
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='campaigns'
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


class Organization(models.Model):
    """
    Represents an organization that owns campaigns and users can be part of.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_organizations'
    )

    def __str__(self):
        return self.name


class UserOrganization(models.Model):
    """
    Represents the many-to-many relationship between users and organizations.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'organization')

    def __str__(self):
        return f'{self.user} in {self.organization}'


class UserCampaign(models.Model):
    """
    Represents the many-to-many relationship between users and campaigns.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'campaign')

    def __str__(self):
        return f'{self.user} in {self.campaign}'
