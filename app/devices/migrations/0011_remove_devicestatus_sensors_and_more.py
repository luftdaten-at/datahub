# Generated by Django 5.1.2 on 2025-01-07 11:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0008_alter_organizationinvitation_expiring_date'),
        ('devices', '0010_device_current_organization'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='devicestatus',
            name='sensors',
        ),
        migrations.AlterField(
            model_name='devicestatus',
            name='device',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_list', to='devices.device'),
        ),
        migrations.CreateModel(
            name='DeviceLogs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('level', models.IntegerField()),
                ('message', models.TextField()),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='devices.device')),
            ],
        ),
        migrations.CreateModel(
            name='Measurement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_received', models.DateTimeField()),
                ('time_measured', models.DateTimeField()),
                ('sensor_model', models.IntegerField()),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='measurements', to='devices.device')),
                ('room', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='measurements', to='campaign.room')),
            ],
        ),
        migrations.CreateModel(
            name='Values',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dimension', models.IntegerField()),
                ('value', models.FloatField()),
                ('measurement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='devices.measurement')),
            ],
        ),
    ]