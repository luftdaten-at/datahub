# Generated by Django 4.2.11 on 2024-03-25 14:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_mobilitymode_airqualityrecord_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='airqualityrecord',
            name='mode',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.mobilitymode'),
        ),
    ]
