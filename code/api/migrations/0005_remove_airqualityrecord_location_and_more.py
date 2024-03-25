# Generated by Django 4.2.11 on 2024-03-23 10:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_remove_airqualityrecord_device_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='airqualityrecord',
            name='location',
        ),
        migrations.AddField(
            model_name='airqualityrecord',
            name='lat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='airqualityrecord',
            name='location_precision',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='airqualityrecord',
            name='lon',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='Location',
        ),
    ]