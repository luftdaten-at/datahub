# Generated by Django 4.2.11 on 2024-04-30 18:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0002_campaign_owner_campaign_public'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaign',
            name='end_date',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='campaign',
            name='start_date',
            field=models.DateTimeField(),
        ),
    ]