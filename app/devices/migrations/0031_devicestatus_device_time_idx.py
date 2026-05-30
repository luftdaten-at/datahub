from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0030_air_station_display_name_station_prefix'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='devicestatus',
            index=models.Index(fields=['device', '-time_received'], name='devicestatus_device_time_idx'),
        ),
    ]
