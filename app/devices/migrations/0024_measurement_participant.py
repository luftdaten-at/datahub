# Generated by Django 5.2 on 2025-05-05 08:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0023_measurement_mode'),
        ('workshops', '0009_alter_workshopimage_workshop'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurement',
            name='participant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='measurements', to='workshops.participant'),
        ),
    ]
