# Generated by Django 5.1.5 on 2025-02-23 22:03

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0019_alter_device_model_alter_modelcounter_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
