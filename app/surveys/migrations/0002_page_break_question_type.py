from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="surveyquestion",
            name="label",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name="surveyquestion",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("range", "Range"),
                    ("likert", "Likert scale"),
                    ("map_points", "Map points"),
                    ("page_break", "Page break"),
                ],
                max_length=16,
            ),
        ),
    ]
