# Generated by Django 4.2.11 on 2024-05-23 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0002_alter_device_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='device',
            name='name',
        ),
        migrations.AddField(
            model_name='device',
            name='device_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='device',
            name='id',
            field=models.CharField(blank=True, max_length=12, primary_key=True, serialize=False),
        ),
    ]
