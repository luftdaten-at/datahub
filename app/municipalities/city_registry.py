"""Fetch and cache api.luftdaten.at /city/all registry data."""

import requests
from django.conf import settings
from django.core.cache import cache

CITY_ALL_CACHE_KEY = "city_all_data"


def load_city_registry_cities():
    """Return (cities, error_message). Caches successful fetches."""
    cities = cache.get(CITY_ALL_CACHE_KEY)
    if cities is not None:
        return cities, None
    try:
        response = requests.get(
            f"{settings.API_URL}/city/all",
            timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        cities = _normalize_cities_from_api(response.json())
        cache.set(
            CITY_ALL_CACHE_KEY,
            cities,
            settings.LUFTDATEN_API_JSON_CACHE_TTL,
        )
        return cities, None
    except (
        requests.exceptions.RequestException,
        ValueError,
        TypeError,
    ) as exc:
        return [], str(exc)


def _normalize_cities_from_api(payload):
    """Turn /city/all JSON into rows for the admin overview template."""
    raw = payload.get("cities", []) if isinstance(payload, dict) else []
    cities = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        loc = item.get("location") or {}
        if not isinstance(loc, dict):
            loc = {}
        country = item.get("country") or {}
        if not isinstance(country, dict):
            country = {}
        country_slug = country.get("slug") or ""
        cities.append(
            {
                "id": item.get("id"),
                "name": item.get("name") or "",
                "slug": item.get("slug") or "",
                "country_name": country.get("name") or "",
                "country_slug": country_slug,
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "country_filter": country_slug,
            }
        )
    cities.sort(
        key=lambda c: ((c["name"] or c["slug"] or "").lower(), c["slug"] or "")
    )
    return cities
