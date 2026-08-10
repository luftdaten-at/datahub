"""Validate and persist survey responses."""

from __future__ import annotations

import json
import uuid

from django.contrib.gis.geos import Point
from django.db import transaction

from .boundary import point_in_boundary
from .models import (
    Answer,
    MapPointAnswer,
    MapPointCategory,
    Survey,
    SurveyQuestion,
    SurveyResponse,
)


class SubmitError(Exception):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__(str(errors))


def _parse_point_choices(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(value) for value in raw if str(value).strip()]
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return [raw.strip()] if raw.strip() else []
        if isinstance(data, list):
            return [str(value) for value in data if str(value).strip()]
        return [raw.strip()] if raw.strip() else []
    return []


def _validate_point_choices(
    point_choices_config: dict,
    selections: list[str],
    *,
    point_index: int,
) -> str | None:
    options = point_choices_config.get("options", [])
    mode = point_choices_config.get("mode", "single")
    for selection in selections:
        if selection not in options:
            return f"Invalid selection for point {point_index + 1}."
    if mode == "single":
        if len(selections) != 1:
            return f"Point {point_index + 1} requires exactly one selection."
    elif len(selections) < 1:
        return f"Point {point_index + 1} requires at least one selection."
    return None


def _parse_map_points(raw: str | list) -> list[dict]:
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SubmitError({"map_points": "Invalid map points JSON."}) from exc
    if not isinstance(data, list):
        raise SubmitError({"map_points": "Map points must be a list."})
    return data


def _parse_multiple_choice_value(raw: str | list | None) -> list[str]:
    if isinstance(raw, list):
        return [str(value) for value in raw if str(value).strip()]
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return [raw.strip()] if raw.strip() else []
        if isinstance(data, list):
            return [str(value) for value in data if str(value).strip()]
        return [raw.strip()] if raw.strip() else []
    return []


def validate_and_submit(
    survey: Survey,
    *,
    payload: dict,
    user=None,
    anonymous_key: str = "",
    client_meta: dict | None = None,
) -> SurveyResponse:
    if not survey.is_accepting_responses:
        raise SubmitError({"survey": "This survey is not accepting responses."})

    if payload.get("website"):
        raise SubmitError({"survey": "Submission rejected."})

    if not survey.boundary:
        raise SubmitError({"survey": "Survey has no boundary defined."})

    errors: dict[str, str] = {}
    questions = list(
        survey.questions.prefetch_related("map_categories").all()
    )

    for question in questions:
        if question.question_type == SurveyQuestion.TYPE_PAGE_BREAK:
            continue
        key = f"q_{question.id}"
        if question.question_type == SurveyQuestion.TYPE_MAP_POINTS:
            q_categories = {c.id: c for c in question.map_categories.all()}
            raw_points = payload.get(key, "[]")
            try:
                points = _parse_map_points(raw_points)
            except SubmitError as exc:
                errors.update(exc.errors)
                continue
            if question.required and not points:
                errors[key] = "At least one map point is required."
                continue
            max_points = question.config.get("max_points", 50)
            if len(points) > max_points:
                errors[key] = f"Maximum {max_points} points allowed."
                continue
            for i, pt in enumerate(points):
                try:
                    lon = float(pt.get("lon"))
                    lat = float(pt.get("lat"))
                    cat_id = int(pt.get("category_id"))
                except (TypeError, ValueError):
                    errors[key] = f"Invalid point data at index {i}."
                    break
                if cat_id not in q_categories:
                    errors[key] = f"Invalid category for point {i + 1}."
                    break
                if not point_in_boundary(lon, lat, survey.boundary):
                    errors[key] = f"Point {i + 1} is outside the survey boundary."
                    break
                point_choices_config = question.config.get("point_choices")
                if point_choices_config:
                    selections = _parse_point_choices(pt.get("choices"))
                    choice_error = _validate_point_choices(
                        point_choices_config, selections, point_index=i
                    )
                    if choice_error:
                        errors[key] = choice_error
                        break
            continue

        if question.question_type == SurveyQuestion.TYPE_MULTIPLE_CHOICE:
            selections = _parse_multiple_choice_value(payload.get(key))
            if question.required and not selections:
                errors[key] = "This field is required."
                continue
            if not selections:
                continue
            options = question.config.get("options", [])
            for selection in selections:
                if selection not in options:
                    errors[key] = "Invalid selection."
                    break
            continue

        value = payload.get(key)
        if question.required and (value is None or value == ""):
            errors[key] = "This field is required."
            continue
        if value is None or value == "":
            continue

        if question.question_type == SurveyQuestion.TYPE_TEXT:
            if not str(value).strip():
                errors[key] = "Text cannot be empty."
        elif question.question_type == SurveyQuestion.TYPE_RANGE:
            try:
                num = float(value)
            except (TypeError, ValueError):
                errors[key] = "Invalid number."
                continue
            lo = question.config.get("min", 0)
            hi = question.config.get("max", 10)
            if num < lo or num > hi:
                errors[key] = f"Value must be between {lo} and {hi}."
        elif question.question_type == SurveyQuestion.TYPE_LIKERT:
            try:
                num = int(value)
            except (TypeError, ValueError):
                errors[key] = "Invalid selection."
                continue
            scale = question.config.get("scale", 5)
            if num < 1 or num > scale:
                errors[key] = f"Value must be between 1 and {scale}."
        elif question.question_type == SurveyQuestion.TYPE_SINGLE_CHOICE:
            options = question.config.get("options", [])
            if str(value) not in options:
                errors[key] = "Invalid selection."

    if errors:
        raise SubmitError(errors)

    if not anonymous_key:
        anonymous_key = str(uuid.uuid4())

    with transaction.atomic():
        response = SurveyResponse.objects.create(
            survey=survey,
            user=user if user and user.is_authenticated else None,
            anonymous_key=anonymous_key,
            client_meta=client_meta or {},
        )

        for question in questions:
            if question.question_type == SurveyQuestion.TYPE_PAGE_BREAK:
                continue
            key = f"q_{question.id}"
            if question.question_type == SurveyQuestion.TYPE_MAP_POINTS:
                q_categories = {c.id: c for c in question.map_categories.all()}
                points = _parse_map_points(payload.get(key, "[]"))
                for pt in points:
                    point_choices_config = question.config.get("point_choices")
                    selections = (
                        _parse_point_choices(pt.get("choices"))
                        if point_choices_config
                        else []
                    )
                    MapPointAnswer.objects.create(
                        response=response,
                        question=question,
                        category=q_categories[int(pt["category_id"])],
                        location=Point(float(pt["lon"]), float(pt["lat"]), srid=4326),
                        comment=str(pt.get("comment", "")).strip(),
                        choices=selections,
                    )
                continue

            if question.question_type == SurveyQuestion.TYPE_MULTIPLE_CHOICE:
                selections = _parse_multiple_choice_value(payload.get(key))
                if not selections:
                    continue
                Answer.objects.create(
                    response=response,
                    question=question,
                    text_value=json.dumps(selections),
                    number_value=None,
                )
                continue

            value = payload.get(key)
            if value is None or value == "":
                continue

            text_value = ""
            number_value = None
            if question.question_type in (
                SurveyQuestion.TYPE_TEXT,
                SurveyQuestion.TYPE_SINGLE_CHOICE,
            ):
                text_value = str(value).strip()
            else:
                number_value = float(value)

            Answer.objects.create(
                response=response,
                question=question,
                text_value=text_value,
                number_value=number_value,
            )

    return response
