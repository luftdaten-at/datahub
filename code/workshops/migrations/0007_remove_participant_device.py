# Generated by Django 4.2.11 on 2024-03-27 10:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0006_participant_device'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='participant',
            name='device',
        ),
    ]