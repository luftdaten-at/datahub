from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Municipality(models.Model):
    """Local mirror of api.luftdaten.at cities enriched with boundary and GKZ."""

    slug = models.SlugField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    country_code = models.CharField(max_length=2, default="AT")

    gkz = models.CharField(max_length=5, null=True, blank=True, db_index=True)

    centroid = gis_models.PointField(srid=4326, null=True, blank=True)
    boundary = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)

    area_km2 = models.FloatField(null=True, blank=True)
    elevation_mean_m = models.FloatField(null=True, blank=True)
    elevation_range_m = models.FloatField(null=True, blank=True)
    population = models.IntegerField(null=True, blank=True)

    MATCH_AUTO = "auto"
    MATCH_MANUAL = "manual"
    MATCH_UNRESOLVED = "unresolved"
    MATCH_CHOICES = [
        (MATCH_AUTO, "Automatisch zugeordnet"),
        (MATCH_MANUAL, "Manuell bestätigt"),
        (MATCH_UNRESOLVED, "Offen"),
    ]
    match_method = models.CharField(
        max_length=16, choices=MATCH_CHOICES, default=MATCH_UNRESOLVED
    )
    match_confidence = models.FloatField(null=True, blank=True)

    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "municipalities"

    def __str__(self):
        return f"{self.name} ({self.slug})"

    @property
    def is_analysable(self):
        return self.boundary is not None and self.match_method != self.MATCH_UNRESOLVED


class PeerGroup(models.Model):
    """Cluster of structurally similar municipalities for fair comparisons."""

    key = models.SlugField(max_length=64, unique=True)
    label_de = models.CharField(max_length=120)
    label_en = models.CharField(max_length=120)
    description_de = models.TextField(blank=True)
    description_en = models.TextField(blank=True)

    def __str__(self):
        return self.label_de


class MunicipalityLandProfile(models.Model):
    """Modul 3 — static Copernicus land indicators."""

    municipality = models.OneToOneField(
        Municipality, on_delete=models.CASCADE, related_name="land_profile"
    )
    peer_group = models.ForeignKey(
        PeerGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    reference_year = models.PositiveSmallIntegerField()

    imperviousness_pct = models.FloatField(null=True)
    imperviousness_change_pp = models.FloatField(null=True)
    tree_cover_pct = models.FloatField(null=True)
    landuse_shares = models.JSONField(default=dict)

    data_source = models.CharField(max_length=32)
    quality_flags = models.JSONField(default=list)
    imported_at = models.DateTimeField(auto_now=True)
    producer_version = models.CharField(max_length=32)


class MunicipalityHeatProfile(models.Model):
    """Modul 6 — LST indicators for a reference day."""

    municipality = models.OneToOneField(
        Municipality, on_delete=models.CASCADE, related_name="heat_profile"
    )

    reference_date = models.DateField(db_index=True)
    acquisition_utc = models.DateTimeField()
    sensor = models.CharField(max_length=32)
    stac_item_id = models.CharField(max_length=160)
    clear_fraction = models.FloatField()

    lst_mean = models.FloatField(null=True)
    lst_p10 = models.FloatField(null=True)
    lst_p90 = models.FloatField(null=True)
    lst_max = models.FloatField(null=True)

    suhi_day = models.FloatField(null=True)
    suhi_night = models.FloatField(null=True)

    dlst_per_10pct_tcd = models.FloatField(null=True)
    dlst_per_10pct_imd = models.FloatField(null=True)
    regression_r2 = models.FloatField(null=True)
    regression_n = models.IntegerField(null=True)

    pop_in_hotspots = models.IntegerField(null=True)
    pop_total = models.IntegerField(null=True)

    lst_by_landuse = models.JSONField(default=dict)
    quality_flags = models.JSONField(default=list)

    imported_at = models.DateTimeField(auto_now=True)
    producer_version = models.CharField(max_length=32)

    class Meta:
        indexes = [models.Index(fields=["reference_date"])]


class DatasetImport(models.Model):
    """Protocol for data intake from external pre-computation."""

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Wartet auf Bestätigung"),
        (STATUS_ACCEPTED, "Übernommen"),
        (STATUS_REJECTED, "Abgelehnt"),
    ]

    module = models.CharField(max_length=16)
    format_version = models.CharField(max_length=16)
    producer = models.CharField(max_length=120, blank=True)
    producer_version = models.CharField(max_length=32, blank=True)
    reference_date = models.DateField(null=True, blank=True)

    source_filename = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64, db_index=True)
    source_path = models.CharField(max_length=512, blank=True)
    generated_utc = models.DateTimeField(null=True, blank=True)

    manifest = models.JSONField(default=dict)
    validation_report = models.JSONField(default=dict)

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    profiles_in_file = models.IntegerField(default=0)
    profiles_written = models.IntegerField(default=0)
    profiles_flagged = models.IntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="context_imports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "source_sha256"],
                name="context_import_unique_payload",
            ),
        ]

    def __str__(self):
        return f"{self.module} {self.reference_date or ''} ({self.status})"


from auditlog.registry import auditlog

auditlog.register(Municipality)
auditlog.register(DatasetImport)
