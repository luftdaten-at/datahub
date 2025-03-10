# Generated by Django 5.1.2 on 2025-01-08 15:17

import django.db.models.deletion
from django.db import migrations, models


def set_invalid_foreign_keys_to_null(apps, schema_editor):
    Campaign = apps.get_model('campaign', 'Campaign')
    for campaign in Campaign.objects.all():
        campaign.organization = None
        campaign.save()


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0008_alter_organizationinvitation_expiring_date'),
        ('devices', '0012_alter_device_current_organization'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(set_invalid_foreign_keys_to_null),
        migrations.RemoveField(
            model_name='organization',
            name='owner',
        ),
        migrations.RemoveField(
            model_name='organization',
            name='users',
        ),
        migrations.AlterField(
            model_name='campaign',
            name='organization',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='campaigns', to='organizations.organization'),
        ),
        migrations.DeleteModel(
            name='OrganizationInvitation',
        ),
        migrations.DeleteModel(
            name='Organization',
        ),
    ]
