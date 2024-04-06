# Generated by Django 4.2.11 on 2024-04-06 04:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0007_alter_device_notes'),
        ('workshops', '0013_remove_participant_device'),
    ]

    operations = [
        migrations.AddField(
            model_name='participant',
            name='device',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='devices.device'),
        ),
    ]
