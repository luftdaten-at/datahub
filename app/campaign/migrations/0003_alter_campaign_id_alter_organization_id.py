# Generated by Django 5.1.2 on 2024-12-10 08:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0002_alter_campaign_id_alter_campaign_name_organization_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaign',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='organization',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
