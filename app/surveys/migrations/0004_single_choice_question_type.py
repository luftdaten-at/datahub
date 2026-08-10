from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0003_question_map_categories"),
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
                    ("map_points", "Map points"),
                    ("page_break", "Page break"),
                ],
                max_length=16,
            ),
        ),
    ]
