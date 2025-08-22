from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from auditlog.registry import auditlog
from auditlog.models import AuditlogHistoryField


class Organization(models.Model):
    """
    Represents an organization that owns campaigns and users can be part of.
    """
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), null=True, blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='organizations')
    history = AuditlogHistoryField()

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_organizations'
    )

    def __str__(self):
        return self.name


class OrganizationInvitation(models.Model):
    """
    if email e gets invited to a campaign
    but there is no usesr with email e
    an invitation is created.

    as soon as users u with email e registers
    user u gets added to all organizations where there
    exists an invitation. -> invitations get deleted
    """
    expiring_date = models.DateField(null=True)
    email = models.EmailField()
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='invitations')
    history = AuditlogHistoryField()

    class Meta:
        unique_together = ('email', 'organization')

    def __str__(self):
        return f'{self.email} {self.organization.name} {self.expiring_date}'

auditlog.register(Organization, m2m_fields={'users'})
auditlog.register(OrganizationInvitation)