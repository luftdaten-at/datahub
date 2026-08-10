"""Sync municipalities from api.luftdaten.at /city/all."""

from __future__ import annotations

from django.contrib.gis.geos import Point

from municipalities.luftdaten_city_admin import COUNTRY_SLUG_TO_ISO
from municipalities.city_registry import load_city_registry_cities

from .models import Municipality


def country_code_from_slug(country_slug: str) -> str:
    slug = (country_slug or "").strip().lower()
    return COUNTRY_SLUG_TO_ISO.get(slug, "AT")


def sync_municipalities_from_api() -> tuple[int, int, str | None]:
    """
    Upsert Municipality rows from /city/all.

    Returns (created_count, updated_count, error_message).
    """
    cities, error = load_city_registry_cities()
    if error:
        return 0, 0, error

    created = 0
    updated = 0
    for city in cities:
        slug = (city.get("slug") or "").strip()
        if not slug:
            continue
        name = city.get("name") or slug
        country_code = country_code_from_slug(city.get("country_slug") or "")
        centroid = None
        lat = city.get("latitude")
        lon = city.get("longitude")
        if lat is not None and lon is not None:
            try:
                centroid = Point(float(lon), float(lat), srid=4326)
            except (TypeError, ValueError):
                centroid = None

        obj, was_created = Municipality.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "country_code": country_code,
                "centroid": centroid,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated, None
