from django.db import migrations, models
import django.db.models.deletion


def copy_survey_categories_to_questions(apps, schema_editor):
    MapPointCategory = apps.get_model("surveys", "MapPointCategory")
    MapPointAnswer = apps.get_model("surveys", "MapPointAnswer")
    SurveyQuestion = apps.get_model("surveys", "SurveyQuestion")

    # Only migrate survey-scoped rows (question not set yet).
    for category in list(
        MapPointCategory.objects.filter(question_id__isnull=True, survey_id__isnull=False)
    ):
        map_questions = list(
            SurveyQuestion.objects.filter(
                survey_id=category.survey_id,
                question_type="map_points",
            ).order_by("order", "id")
        )
        if not map_questions:
            category.delete()
            continue

        # Reuse the existing row for the first map question so answer FKs stay valid.
        first = map_questions[0]
        category.question_id = first.id
        category.save(update_fields=["question_id"])

        for question in map_questions[1:]:
            new_category = MapPointCategory.objects.create(
                survey_id=category.survey_id,
                question_id=question.id,
                key=category.key,
                label=category.label,
                color=category.color,
                order=category.order,
            )
            MapPointAnswer.objects.filter(
                category_id=category.id,
                question_id=question.id,
            ).update(category_id=new_category.id)


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0002_page_break_question_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="mappointcategory",
            name="question",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="map_categories",
                to="surveys.surveyquestion",
            ),
        ),
        # Drop (survey, key) before copying so multiple question rows can share a key.
        migrations.AlterUniqueTogether(
            name="mappointcategory",
            unique_together=set(),
        ),
        migrations.RunPython(
            copy_survey_categories_to_questions,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="mappointcategory",
            name="survey",
        ),
        migrations.AlterField(
            model_name="mappointcategory",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="map_categories",
                to="surveys.surveyquestion",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="mappointcategory",
            unique_together={("question", "key")},
        ),
    ]
