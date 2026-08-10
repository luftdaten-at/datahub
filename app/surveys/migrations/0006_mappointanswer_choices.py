from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0005_multiple_choice_question_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="mappointanswer",
            name="choices",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
