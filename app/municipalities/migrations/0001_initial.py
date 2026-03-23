import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _forwards(apps, schema_editor):
    # RunPython receives from_state.apps: "municipalities" is not registered yet,
    # so we cannot apps.get_model("municipalities", ...). Use SQL for fresh DB.
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

    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    user_table = User._meta.db_table
    qn = connection.ops.quote_name
    sql = (
        f"CREATE TABLE {qn(new_table)} ("
        f"{qn('id')} BIGSERIAL NOT NULL PRIMARY KEY, "
        f"{qn('municipality_slug')} VARCHAR(128) NOT NULL, "
        f"{qn('created_at')} TIMESTAMPTZ NOT NULL, "
        f"{qn('user_id')} BIGINT NOT NULL "
        f"REFERENCES {qn(user_table)} ({qn('id')}) "
        f"DEFERRABLE INITIALLY DEFERRED, "
        f"CONSTRAINT {qn('municipalities_favorite_user_municipality_slug_unique')} "
        f"UNIQUE ({qn('user_id')}, {qn('municipality_slug')})"
        f")"
    )
    with connection.cursor() as cursor:
        cursor.execute(sql)


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
