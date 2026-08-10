"""Helpers for per-question map point categories."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import MapPointCategory, SurveyQuestion

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normalize_map_categories(categories_raw) -> list[dict]:
    if not isinstance(categories_raw, list):
        raise ValidationError("Categories must be a list.")
    if not categories_raw:
        raise ValidationError("At least one category is required.")
    if len(categories_raw) != 1:
        raise ValidationError("Exactly one category is required.")
    normalized = []
    seen_keys: set[str] = set()
    for index, raw in enumerate(categories_raw):
        if not isinstance(raw, dict):
            raise ValidationError("Each category must be an object.")
        key = slugify(str(raw.get("key", "")).strip())[:64]
        if not key:
            raise ValidationError("Each category needs a key.")
        if key in seen_keys:
            raise ValidationError(f"Duplicate category key: {key}")
        seen_keys.add(key)
        label = str(raw.get("label", "")).strip()
        if not label:
            raise ValidationError("Each category needs a label.")
        color = str(raw.get("color", "#3388ff")).strip().lower()
        if not HEX_COLOR_RE.match(color):
            raise ValidationError(f"Invalid color for category '{key}'.")
        normalized.append({"key": key, "label": label, "color": color, "order": index})
    return normalized


def sync_map_categories(question: SurveyQuestion, categories: list[dict]) -> None:
    if question.question_type != SurveyQuestion.TYPE_MAP_POINTS:
        return

    existing = {c.key: c for c in question.map_categories.all()}
    seen_keys: set[str] = set()
    for index, cat in enumerate(categories):
        key = cat["key"]
        seen_keys.add(key)
        if key in existing:
            obj = existing[key]
            obj.label = cat["label"]
            obj.color = cat["color"]
            obj.order = index
            obj.save(update_fields=["label", "color", "order"])
        else:
            MapPointCategory.objects.create(
                question=question,
                key=key,
                label=cat["label"],
                color=cat["color"],
                order=index,
            )

    for key, obj in existing.items():
        if key not in seen_keys:
            if obj.points.exists():
                raise ValidationError(
                    f"Cannot remove category '{key}' because it has responses."
                )
            obj.delete()
