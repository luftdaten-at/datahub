# Device display name: "Station {n}" instead of "Air Station {n}" for product Air Station (model=3).

from django.db import migrations


def forwards(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    qs = Device.objects.filter(model=3).exclude(auto_number__isnull=True)
    for d in qs.iterator():
        new_name = f"Station {int(d.auto_number)}"
        if d.device_name != new_name:
            Device.objects.filter(pk=d.pk).update(device_name=new_name)


def backwards(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    qs = Device.objects.filter(model=3).exclude(auto_number__isnull=True)
    for d in qs.iterator():
        old_name = f"Air Station {int(d.auto_number)}"
        Device.objects.filter(pk=d.pk).update(device_name=old_name)


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0029_air_station_device_name_unpadded"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
