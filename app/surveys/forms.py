from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from context.models import Municipality

from .map_categories import normalize_map_categories, sync_map_categories
from .models import MapPointCategory, Survey, SurveyQuestion


class SurveyForm(forms.ModelForm):
    boundary_file = forms.FileField(required=False, label="Boundary (GeoJSON or GeoPackage)")

    class Meta:
        model = Survey
        fields = [
            "municipality",
            "title",
            "slug",
            "description",
            "opens_at",
            "closes_at",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "opens_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "closes_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["municipality"].queryset = Municipality.objects.order_by("name")
        if not self.instance.pk and not self.initial.get("slug"):
            self.fields["slug"].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or ""
        if not slug and self.cleaned_data.get("title"):
            slug = slugify(self.cleaned_data["title"])[:128]
        if not slug:
            raise forms.ValidationError("Slug is required.")
        return slug


def normalize_point_choices(point_choices_raw) -> dict | None:
    if not point_choices_raw:
        return None
    if not isinstance(point_choices_raw, dict):
        raise ValidationError("Point choices must be an object.")
    mode = str(point_choices_raw.get("mode", "")).strip()
    if mode not in ("single", "multiple"):
        raise ValidationError("Point choice mode must be single or multiple.")
    help_text = str(point_choices_raw.get("help_text", "")).strip()
    if len(help_text) > 500:
        raise ValidationError("Point choice helper text must be at most 500 characters.")
    options = normalize_choice_options(point_choices_raw.get("options", []))
    result = {"mode": mode, "options": options}
    if help_text:
        result["help_text"] = help_text
    return result


def normalize_choice_options(options_raw) -> list[str]:
    if not isinstance(options_raw, list):
        raise ValidationError("Options must be a list.")
    if len(options_raw) < 2:
        raise ValidationError("At least two options are required.")
    options = []
    seen: set[str] = set()
    for raw in options_raw:
        label = str(raw).strip()
        if not label:
            raise ValidationError("Each option needs a label.")
        if len(label) > 200:
            raise ValidationError("Option labels must be at most 200 characters.")
        if label in seen:
            raise ValidationError(f"Duplicate option: {label}")
        seen.add(label)
        options.append(label)
    return options


def normalize_question_config(question_type, config=None):
    """Validate and normalize config dict for a question type."""
    config = dict(config or {})
    if question_type == SurveyQuestion.TYPE_TEXT:
        return {}

    if question_type == SurveyQuestion.TYPE_RANGE:
        try:
            lo = float(config.get("min", 0))
            hi = float(config.get("max", 10))
        except (TypeError, ValueError) as exc:
            raise ValidationError("Range min and max must be numbers.") from exc
        if lo >= hi:
            raise ValidationError("Range min must be less than max.")
        return {"min": lo, "max": hi}

    if question_type == SurveyQuestion.TYPE_LIKERT:
        try:
            scale = int(config.get("scale", 5))
        except (TypeError, ValueError) as exc:
            raise ValidationError("Likert scale must be an integer.") from exc
        if scale < 1:
            raise ValidationError("Likert scale must be at least 1.")
        return {"scale": scale}

    if question_type in (
        SurveyQuestion.TYPE_SINGLE_CHOICE,
        SurveyQuestion.TYPE_MULTIPLE_CHOICE,
    ):
        return {"options": normalize_choice_options(config.get("options", []))}

    if question_type == SurveyQuestion.TYPE_MAP_POINTS:
        try:
            max_points = int(config.get("max_points", 50))
        except (TypeError, ValueError) as exc:
            raise ValidationError("Max points must be an integer.") from exc
        if max_points < 1:
            raise ValidationError("Max points must be at least 1.")
        categories = normalize_map_categories(config.get("categories", []))
        result = {"max_points": max_points, "categories": categories}
        point_choices = normalize_point_choices(config.get("point_choices"))
        if point_choices:
            result["point_choices"] = point_choices
        return result

    if question_type == SurveyQuestion.TYPE_PAGE_BREAK:
        return {}

    raise ValidationError(f"Unknown question type: {question_type}")


class SurveyQuestionForm(forms.ModelForm):
    class Meta:
        model = SurveyQuestion
        fields = ["question_type", "label", "help_text", "required", "order"]
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "help_text": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, config=None, **kwargs):
        self._config_input = config
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        question_type = cleaned.get("question_type")
        if not question_type:
            return cleaned
        config_input = self._config_input
        if config_input is None and self.instance.pk:
            config_input = self.instance.config
        try:
            cleaned["config"] = normalize_question_config(question_type, config_input)
        except ValidationError as exc:
            self.add_error(None, exc)
        if question_type == SurveyQuestion.TYPE_PAGE_BREAK:
            cleaned["required"] = False
        elif not cleaned.get("label"):
            self.add_error("label", _("Label is required."))
        return cleaned

    def save(self, commit=True):
        if "config" in self.cleaned_data:
            self.instance.config = self.cleaned_data["config"]
        return super().save(commit=commit)


class MapPointCategoryForm(forms.ModelForm):
    HEX_COLOR_VALIDATOR = RegexValidator(
        regex=r"^#[0-9A-Fa-f]{6}$",
        message=_("Enter a valid hex color (e.g. #3388ff)."),
    )

    class Meta:
        model = MapPointCategory
        fields = ["key", "label", "color"]
        help_texts = {
            "key": _(
                "Stable slug used internally (e.g. tree, bench). Lowercase letters, numbers, and hyphens."
            ),
            "label": _("Name shown to respondents when they pick a category for a map point."),
            "color": _("Hex color for points of this category on the map (e.g. #3388ff)."),
        }

    def clean_color(self):
        color = (self.cleaned_data.get("color") or "").strip()
        self.HEX_COLOR_VALIDATOR(color)
        return color.lower()
