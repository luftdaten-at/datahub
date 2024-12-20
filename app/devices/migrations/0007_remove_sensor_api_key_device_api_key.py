# Generated by Django 5.1.2 on 2024-12-20 11:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0006_sensor_api_key'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sensor',
            name='api_key',
        ),
        migrations.AddField(
            model_name='device',
            name='api_key',
            field=models.CharField(max_length=64, null=True),
        ),
    ]
