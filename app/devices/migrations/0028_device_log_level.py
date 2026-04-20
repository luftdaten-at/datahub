import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0027_device_calibration_mode_device_test_mode_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="log_level",
            field=models.IntegerField(
                blank=True,
                help_text="Desired status log level (0=debug .. 4=critical). Sent to device via POST /devices/status/ when it differs from the latest line.",
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(4),
                ],
            ),
        ),
    ]
