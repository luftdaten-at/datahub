# Generated by Django 4.2.11 on 2024-03-25 14:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0003_alter_workshop_description'),
    ]

    operations = [
        migrations.RenameField(
            model_name='workshop',
            old_name='id',
            new_name='name',
        ),
    ]