from api.models import AirQualityRecord, Location
from devices.models import Device, Measurement, Values
from main import enums

from django.contrib.gis.geos import Point
from django.utils.timezone import now


TRANSLATE = '''B8ADBB1D0470AAA
D83BDA6D3D2CAAA
28372F821AE4AAA
D83BDA6E3FF0AAA
28372F8080A0AAA
28372F821B10AAA
28372F808088AAA
28372F8080ACAAA
D83BDA6E3838AAA
28372F808414AAA
D83BDA6E3800AAA
D83BDA6E37DCAAA
28372F808060AAA
28372F808064AAA
28372F807B70AAA
28372F842FA0AAA
28372F808084AAA
D83BDA6E37D4AAA
28372F808438AAA
D83BDA6E37B4AAA
D83BDA6E4034AAA
28372F821ADCAAA
28372F821AC8AAA'''

def migrate_air_quality_records():
    device_set = set([d for d in TRANSLATE.split('\n')])

    for record in AirQualityRecord.objects.all():
        new_device_id = None
        if record.device.id in device_set:
            id_num = int(record.device.id, 16) + 0x1000
            new_device_id = hex(id_num).upper()
        else:
            new_device_id = record.device.id
        
        # Optional: Create Location if lat/lon exist
        location = None
        if record.lat is not None and record.lon is not None:
            location, _ = Location.objects.get_or_create(
                coordinates=Point(record.lon, record.lat),
                height=None
            )
        
        # Create Measurement
        measurement, created = Measurement.objects.get_or_create(
            time_measured=record.time,
            time_received=now(),  # or record.time if you don't have a separate received timestamp
            sensor_model=enums.SensorModel.SEN5X,  # replace with actual model ID if known
            device=Device.objects.filter(id = new_device_id).first(),
            room=None,  # Assign if you can map from record
            user=None,
            workshop=record.workshop,
            location=location,
            mode=record.mode,
            participant=record.participant
        )

        if not created:
            print(f"Skipping record {record.id} already has an existing Measurement {measurement.id}")
            continue

        # Create Values
        for field, dimension_id in enums.AQR_DIMENSION_MAP.items():
            value = getattr(record, field)
            if value is not None:
                Values.objects.create(
                    dimension=dimension_id,
                    value=value,
                    measurement=measurement
                )

        print(f"Migrated record {record.id} to measurement {measurement.id}")

