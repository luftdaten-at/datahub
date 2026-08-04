from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Municipality",
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
                ("slug", models.SlugField(db_index=True, max_length=128, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("country_code", models.CharField(default="AT", max_length=2)),
                (
                    "gkz",
                    models.CharField(
                        blank=True, db_index=True, max_length=5, null=True
                    ),
                ),
                (
                    "centroid",
                    gis_models.PointField(blank=True, null=True, srid=4326),
                ),
                (
                    "boundary",
                    gis_models.MultiPolygonField(blank=True, null=True, srid=4326),
                ),
                ("area_km2", models.FloatField(blank=True, null=True)),
                ("elevation_mean_m", models.FloatField(blank=True, null=True)),
                ("elevation_range_m", models.FloatField(blank=True, null=True)),
                ("population", models.IntegerField(blank=True, null=True)),
                (
                    "match_method",
                    models.CharField(
                        choices=[
                            ("auto", "Automatisch zugeordnet"),
                            ("manual", "Manuell bestätigt"),
                            ("unresolved", "Offen"),
                        ],
                        default="unresolved",
                        max_length=16,
                    ),
                ),
                ("match_confidence", models.FloatField(blank=True, null=True)),
                ("synced_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name_plural": "municipalities",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PeerGroup",
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
                ("key", models.SlugField(max_length=64, unique=True)),
                ("label_de", models.CharField(max_length=120)),
                ("label_en", models.CharField(max_length=120)),
                ("description_de", models.TextField(blank=True)),
                ("description_en", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="DatasetImport",
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
                ("module", models.CharField(max_length=16)),
                ("format_version", models.CharField(max_length=16)),
                ("producer", models.CharField(blank=True, max_length=120)),
                ("producer_version", models.CharField(blank=True, max_length=32)),
                ("reference_date", models.DateField(blank=True, null=True)),
                ("source_filename", models.CharField(max_length=255)),
                ("source_sha256", models.CharField(db_index=True, max_length=64)),
                ("source_path", models.CharField(blank=True, max_length=512)),
                ("generated_utc", models.DateTimeField(blank=True, null=True)),
                ("manifest", models.JSONField(default=dict)),
                ("validation_report", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Wartet auf Bestätigung"),
                            ("accepted", "Übernommen"),
                            ("rejected", "Abgelehnt"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("profiles_in_file", models.IntegerField(default=0)),
                ("profiles_written", models.IntegerField(default=0)),
                ("profiles_flagged", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="context_imports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="MunicipalityLandProfile",
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
                ("reference_year", models.PositiveSmallIntegerField()),
                ("imperviousness_pct", models.FloatField(null=True)),
                ("imperviousness_change_pp", models.FloatField(null=True)),
                ("tree_cover_pct", models.FloatField(null=True)),
                ("landuse_shares", models.JSONField(default=dict)),
                ("data_source", models.CharField(max_length=32)),
                ("quality_flags", models.JSONField(default=list)),
                ("imported_at", models.DateTimeField(auto_now=True)),
                ("producer_version", models.CharField(max_length=32)),
                (
                    "municipality",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="land_profile",
                        to="context.municipality",
                    ),
                ),
                (
                    "peer_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="members",
                        to="context.peergroup",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MunicipalityHeatProfile",
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
                ("reference_date", models.DateField(db_index=True)),
                ("acquisition_utc", models.DateTimeField()),
                ("sensor", models.CharField(max_length=32)),
                ("stac_item_id", models.CharField(max_length=160)),
                ("clear_fraction", models.FloatField()),
                ("lst_mean", models.FloatField(null=True)),
                ("lst_p10", models.FloatField(null=True)),
                ("lst_p90", models.FloatField(null=True)),
                ("lst_max", models.FloatField(null=True)),
                ("suhi_day", models.FloatField(null=True)),
                ("suhi_night", models.FloatField(null=True)),
                ("dlst_per_10pct_tcd", models.FloatField(null=True)),
                ("dlst_per_10pct_imd", models.FloatField(null=True)),
                ("regression_r2", models.FloatField(null=True)),
                ("regression_n", models.IntegerField(null=True)),
                ("pop_in_hotspots", models.IntegerField(null=True)),
                ("pop_total", models.IntegerField(null=True)),
                ("lst_by_landuse", models.JSONField(default=dict)),
                ("quality_flags", models.JSONField(default=list)),
                ("imported_at", models.DateTimeField(auto_now=True)),
                ("producer_version", models.CharField(max_length=32)),
                (
                    "municipality",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="heat_profile",
                        to="context.municipality",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="datasetimport",
            constraint=models.UniqueConstraint(
                fields=("module", "source_sha256"),
                name="context_import_unique_payload",
            ),
        ),
        migrations.AddIndex(
            model_name="municipalityheatprofile",
            index=models.Index(
                fields=["reference_date"], name="context_mun_referen_idx"
            ),
        ),
    ]
