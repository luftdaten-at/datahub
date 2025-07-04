from django.db import migrations
from django.contrib.gis.geos import Point

def populate_location(apps, schema_editor):
    AirQualityRecord = apps.get_model('api', 'AirQualityRecord')
    Location = apps.get_model('api', 'Location')

    for record in AirQualityRecord.objects.all():
        if record.lat is not None and record.lon is not None:
            # Create a new Location object
            location = Location.objects.create(coordinates=Point(record.lon, record.lat))
            # Assign the new Location to the AirQualityRecord
            record.location = location
            record.save()

def reverse_migration(apps, schema_editor):
    AirQualityRecord = apps.get_model('api', 'AirQualityRecord')
    #Location = apps.get_model('api', 'Location')

    for record in AirQualityRecord.objects.all():
        if record.location:
            # Extract lat and lon from the Location object
            record.lat = record.location.coordinates.y
            record.lon = record.location.coordinates.x
            record.save()

    # Optionally, delete all Location objects
    #Location.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_airqualityrecord_location'),
    ]

    operations = [
        migrations.RunPython(populate_location, reverse_migration),
    ]
