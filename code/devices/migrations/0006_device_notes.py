# Generated by Django 4.2.11 on 2024-03-30 14:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0005_firmwareversion_device_firmware_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='notes',
            field=models.TextField(null=True),
        ),
    ]