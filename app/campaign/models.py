from django.db import models
from django.conf import settings
import string
import random

class Campaign(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    public = models.BooleanField(default=True)
    id_token = models.CharField(max_length=8, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_campaigns',  # Allows user.owned_campaigns.all() to get all owned workshops
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.id_token:
            # Generate a unique ID for new workshops
            self.id_token = self.generate_id_token()
        super(Campaign, self).save(*args, **kwargs)

    @staticmethod
    def generate_id_token():
        length = 8
        # Ensure the generated ID is unique
        while Campaign.objects.filter(id_token=id_token).exists():
            # Generate a random string of letters and digits
            id_token = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        return id_token