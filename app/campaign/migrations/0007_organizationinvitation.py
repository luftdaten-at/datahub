# Generated by Django 5.1.2 on 2024-12-18 09:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0006_alter_campaign_users_alter_organization_users'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganizationInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expiring_date', models.DateField()),
                ('email', models.EmailField(max_length=254)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='campaign.organization')),
            ],
            options={
                'unique_together': {('email', 'organization')},
            },
        ),
    ]
