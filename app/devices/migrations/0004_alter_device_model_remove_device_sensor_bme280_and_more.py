# Generated by Django 5.1.2 on 2024-12-09 07:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0003_remove_device_name_device_device_name_and_more'),
        ('api', '0001_initial')
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='model',
            field=models.CharField(blank=True, max_length=255, null=True),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='device',
            name='sensor_bme280',
        ),
        migrations.RemoveField(
            model_name='device',
            name='sensor_bme680',
        ),
        migrations.RemoveField(
            model_name='device',
            name='sensor_sen5x',
        ),
        migrations.RemoveField(
            model_name='sensor',
            name='description',
        ),
        migrations.AddField(
            model_name='device',
            name='firmware',
            field=models.CharField(blank=True, max_length=12),
        ),
        migrations.AddField(
            model_name='sensor',
            name='firmware',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='sensor',
            name='hardware',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='sensor',
            name='product_type',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='sensor',
            name='protocol',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='sensor',
            name='serial',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='device',
            name='device_name',
            field=models.CharField(blank=True, max_length=255, null=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='device',
            name='id',
            field=models.CharField(max_length=255, primary_key=True, serialize=False),
        ),
        migrations.RunSQL(
            "ALTER TABLE api_measurement DROP CONSTRAINT api_measurement_sensor_id_8039993a_fk_devices_sensor_name;",  # PostgreSQL example
            "ALTER TABLE api_measurement ADD CONSTRAINT api_measurement_sensor_id_8039993a_fk_devices_sensor_name FOREIGN KEY (sensor) REFERENCES devices_sensor(name);"
        ),
        migrations.AlterField(
            model_name='sensor',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AddField(
            model_name='sensor',
            name='id',
            field=models.CharField(max_length=255, primary_key=True),
        ),
        migrations.DeleteModel(
            name='DeviceModel',
        ),
    ]
