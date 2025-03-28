# Generated by Django 5.1.2 on 2024-12-10 09:22

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0004_alter_campaign_organization'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='userorganization',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='userorganization',
            name='organization',
        ),
        migrations.RemoveField(
            model_name='userorganization',
            name='user',
        ),
        migrations.AddField(
            model_name='campaign',
            name='users',
            field=models.ManyToManyField(related_name='campaign', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='organization',
            name='users',
            field=models.ManyToManyField(related_name='organization', to=settings.AUTH_USER_MODEL),
        ),
        migrations.DeleteModel(
            name='UserCampaign',
        ),
        migrations.DeleteModel(
            name='UserOrganization',
        ),
    ]
