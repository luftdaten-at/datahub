from django.db import models
import string
import random

class Workshop(models.Model):
    id = models.CharField(max_length=6, unique=True, primary_key=True, blank=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.id:
            # Generate a unique ID for new workshops
            self.id = self.generate_id()
        super(Workshop, self).save(*args, **kwargs)

    @staticmethod
    def generate_id():
        length = 6
        # Generate a random string of letters and digits
        id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        
        # Ensure the generated ID is unique
        while Workshop.objects.filter(id=id).exists():
            id = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        return id