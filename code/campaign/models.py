from django.db import models
from django.conf import settings

class Campaign(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    public = models.BooleanField(default=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_campaigns',  # Allows user.owned_campaigns.all() to get all owned workshops
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name