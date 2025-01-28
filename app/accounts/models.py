from django.contrib.auth.models import AbstractUser
from django.db import models
from auditlog.registry import auditlog
from auditlog.models import AuditlogHistoryField


class CustomUser(AbstractUser):
    history = AuditlogHistoryField()


auditlog.register(CustomUser)