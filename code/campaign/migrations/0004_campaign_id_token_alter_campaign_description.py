# Generated by Django 4.2.11 on 2024-05-01 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0003_alter_campaign_end_date_alter_campaign_start_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='id_token',
            field=models.CharField(max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='campaign',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
