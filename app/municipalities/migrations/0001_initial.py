import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _forwards(apps, schema_editor):
    connection = schema_editor.connection
    old_table = "cities_favoritecity"
    new_table = "municipalities_favoritemunicipality"
    with connection.cursor() as cursor:
        existing = set(connection.introspection.table_names())
        if new_table in existing:
            return
        if old_table in existing:
            qn = connection.ops.quote_name
            cursor.execute(
                f"ALTER TABLE {qn(old_table)} RENAME TO {qn(new_table)}"
            )
            cursor.execute(
                f"ALTER TABLE {qn(new_table)} RENAME COLUMN city_slug TO municipality_slug"
            )
            cursor.execute(
                f"ALTER TABLE {qn(new_table)} RENAME CONSTRAINT "
                f"{qn('cities_favorite_user_city_slug_unique')} TO "
                f"{qn('municipalities_favorite_user_municipality_slug_unique')}"
            )
            return
    FavoriteMunicipality = apps.get_model(
        "municipalities", "FavoriteMunicipality"
    )
    schema_editor.create_model(FavoriteMunicipality)


def _backwards(apps, schema_editor):
    connection = schema_editor.connection
    old_table = "cities_favoritecity"
    new_table = "municipalities_favoritemunicipality"
    with connection.cursor() as cursor:
        existing = set(connection.introspection.table_names())
        if old_table in existing:
            return
        if new_table not in existing:
            return
        qn = connection.ops.quote_name
        cursor.execute(
            f"ALTER TABLE {qn(new_table)} RENAME CONSTRAINT "
            f"{qn('municipalities_favorite_user_municipality_slug_unique')} TO "
            f"{qn('cities_favorite_user_city_slug_unique')}"
        )
        cursor.execute(
            f"ALTER TABLE {qn(new_table)} RENAME COLUMN municipality_slug TO city_slug"
        )
        cursor.execute(
            f"ALTER TABLE {qn(new_table)} RENAME TO {qn(old_table)}"
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="FavoriteMunicipality",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "municipality_slug",
                            models.CharField(max_length=128),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(auto_now_add=True),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="favorite_municipalities",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["-created_at"],
                    },
                ),
                migrations.AddConstraint(
                    model_name="favoritemunicipality",
                    constraint=models.UniqueConstraint(
                        fields=("user", "municipality_slug"),
                        name="municipalities_favorite_user_municipality_slug_unique",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(_forwards, _backwards),
            ],
        ),
    ]
