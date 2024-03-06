# Generated by Django 4.2.6 on 2024-03-05 21:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='sensor_sen5x',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='device',
            name='board_id',
            field=models.CharField(max_length=12, null=True),
        ),
        migrations.AlterField(
            model_name='device',
            name='btmac_address',
            field=models.CharField(max_length=12, null=True),
        ),
    ]
