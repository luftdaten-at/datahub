from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0004_single_choice_question_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="surveyquestion",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("range", "Range"),
                    ("likert", "Likert scale"),
                    ("single_choice", "Single choice"),
                    ("multiple_choice", "Multiple choice"),
                    ("map_points", "Map points"),
                    ("page_break", "Page break"),
                ],
                max_length=16,
            ),
        ),
    ]
