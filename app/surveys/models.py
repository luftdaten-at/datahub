from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Survey(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, _("Draft")),
        (STATUS_PUBLISHED, _("Published")),
        (STATUS_CLOSED, _("Closed")),
    ]

    municipality = models.ForeignKey(
        "context.Municipality",
        on_delete=models.PROTECT,
        related_name="surveys",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    boundary = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_surveys",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_accepting_responses(self):
        if self.status != self.STATUS_PUBLISHED:
            return False
        now = timezone.now()
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now > self.closes_at:
            return False
        return True


class SurveyQuestion(models.Model):
    TYPE_TEXT = "text"
    TYPE_RANGE = "range"
    TYPE_LIKERT = "likert"
    TYPE_SINGLE_CHOICE = "single_choice"
    TYPE_MULTIPLE_CHOICE = "multiple_choice"
    TYPE_MAP_POINTS = "map_points"
    TYPE_PAGE_BREAK = "page_break"
    TYPE_CHOICES = [
        (TYPE_TEXT, _("Text")),
        (TYPE_RANGE, _("Range")),
        (TYPE_LIKERT, _("Likert scale")),
        (TYPE_SINGLE_CHOICE, _("Single choice")),
        (TYPE_MULTIPLE_CHOICE, _("Multiple choice")),
        (TYPE_MAP_POINTS, _("Map points")),
        (TYPE_PAGE_BREAK, _("Page break")),
    ]

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="questions"
    )
    question_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    label = models.CharField(max_length=500, blank=True)
    help_text = models.CharField(max_length=500, blank=True)
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.label} ({self.question_type})"


class MapPointCategory(models.Model):
    question = models.ForeignKey(
        SurveyQuestion, on_delete=models.CASCADE, related_name="map_categories"
    )
    key = models.SlugField(max_length=64)
    label = models.CharField(max_length=120)
    color = models.CharField(max_length=7, default="#3388ff")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("question", "key")]

    def __str__(self):
        return self.label


class SurveyResponse(models.Model):
    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="responses"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_responses",
    )
    anonymous_key = models.CharField(max_length=64, blank=True, db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    client_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Response to {self.survey.slug} at {self.submitted_at}"


class Answer(models.Model):
    response = models.ForeignKey(
        SurveyResponse, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        SurveyQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    text_value = models.TextField(blank=True)
    number_value = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = [("response", "question")]

    def __str__(self):
        return f"Answer to Q{self.question_id}"


class MapPointAnswer(models.Model):
    response = models.ForeignKey(
        SurveyResponse, on_delete=models.CASCADE, related_name="map_points"
    )
    question = models.ForeignKey(
        SurveyQuestion, on_delete=models.CASCADE, related_name="map_point_answers"
    )
    category = models.ForeignKey(
        MapPointCategory, on_delete=models.PROTECT, related_name="points"
    )
    location = gis_models.PointField(srid=4326)
    comment = models.TextField(blank=True)
    choices = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Point at {self.location}"


from auditlog.registry import auditlog

auditlog.register(Survey)
auditlog.register(SurveyResponse)
