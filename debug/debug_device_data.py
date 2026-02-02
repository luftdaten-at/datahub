#!/usr/bin/env python
"""
Debug script to check device data relationships
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.main.settings')
django.setup()

from devices.models import Device, Measurement
from workshops.models import Workshop
from api.models import AirQualityRecord

device_id = "D83BDA6E37DCAAA"
workshop_name = "cvuid8"

print(f"Checking device: {device_id}")
print(f"Checking workshop: {workshop_name}")
print("=" * 60)

# Check if device exists
try:
    device = Device.objects.get(id=device_id)
    print(f"✓ Device found: {device.device_name or device.id}")
except Device.DoesNotExist:
    print(f"✗ Device {device_id} not found!")
    sys.exit(1)

# Check if workshop exists
try:
    workshop = Workshop.objects.get(name=workshop_name)
    print(f"✓ Workshop found: {workshop.title}")
except Workshop.DoesNotExist:
    print(f"✗ Workshop {workshop_name} not found!")
    sys.exit(1)

print("\n" + "=" * 60)
print("Checking Measurement model:")
print("=" * 60)
measurements = Measurement.objects.filter(device=device, workshop=workshop)
print(f"Measurements count: {measurements.count()}")
if measurements.exists():
    print(f"First measurement: {measurements.order_by('time_measured').first().time_measured}")
    print(f"Last measurement: {measurements.order_by('-time_measured').first().time_measured}")

print("\n" + "=" * 60)
print("Checking AirQualityRecord model:")
print("=" * 60)
aqr_records = AirQualityRecord.objects.filter(device=device, workshop=workshop)
print(f"AirQualityRecord count: {aqr_records.count()}")
if aqr_records.exists():
    print(f"First record: {aqr_records.order_by('time').first().time}")
    print(f"Last record: {aqr_records.order_by('-time').first().time}")

print("\n" + "=" * 60)
print("Checking all workshops for this device:")
print("=" * 60)

# Check workshops from Measurement
workshops_from_measurements = Workshop.objects.filter(measurements__device=device).distinct()
print(f"\nWorkshops from Measurement model: {workshops_from_measurements.count()}")
for w in workshops_from_measurements:
    count = Measurement.objects.filter(device=device, workshop=w).count()
    print(f"  - {w.name} ({w.title}): {count} measurements")

# Check workshops from AirQualityRecord
workshops_from_aqr = Workshop.objects.filter(air_quality_records__device=device).distinct()
print(f"\nWorkshops from AirQualityRecord model: {workshops_from_aqr.count()}")
for w in workshops_from_aqr:
    count = AirQualityRecord.objects.filter(device=device, workshop=w).count()
    print(f"  - {w.name} ({w.title}): {count} records")

print("\n" + "=" * 60)
print("Summary:")
print("=" * 60)
all_workshop_ids = set()
all_workshop_ids.update(workshops_from_measurements.values_list('pk', flat=True))
all_workshop_ids.update(workshops_from_aqr.values_list('pk', flat=True))
print(f"Total unique workshops: {len(all_workshop_ids)}")
if workshop.pk in all_workshop_ids:
    print(f"✓ Workshop {workshop_name} IS found in device data!")
else:
    print(f"✗ Workshop {workshop_name} is NOT found in device data!")

