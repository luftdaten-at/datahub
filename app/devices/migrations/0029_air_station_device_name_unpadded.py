# Data migration: Air Station device_name without leading zeros in the number.

from django.db import migrations


def forwards(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    # LdProduct.AIR_STATION == 3
    qs = Device.objects.filter(model=3).exclude(auto_number__isnull=True)
    for d in qs.iterator():
        new_name = f"Air Station {int(d.auto_number)}"
        if d.device_name != new_name:
            Device.objects.filter(pk=d.pk).update(device_name=new_name)


def backwards(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    qs = Device.objects.filter(model=3).exclude(auto_number__isnull=True)
    for d in qs.iterator():
        old_name = f"Air Station {int(d.auto_number):04d}"
        Device.objects.filter(pk=d.pk).update(device_name=old_name)


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0028_device_log_level"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
