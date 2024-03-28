# Generated by Django 4.2.11 on 2024-03-28 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0009_participant_device'),
    ]

    operations = [
        migrations.AddField(
            model_name='workshop',
            name='mapbox_bottom_left_lat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workshop',
            name='mapbox_bottom_left_lon',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workshop',
            name='mapbox_bottom_right_lat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workshop',
            name='mapbox_bottom_right_lon',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workshop',
            name='mapbox_top_left_lat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workshop',
            name='mapbox_top_left_lon',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workshop',
            name='mapbox_top_right_lon',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workshop',
            name='mapbox_topr_ight_lat',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
