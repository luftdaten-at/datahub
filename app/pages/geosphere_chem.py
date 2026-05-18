"""GeoSphere chem forecast API helpers (chem-v2-1h-3km proxy)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from requests.exceptions import RequestException

CHEM_ALLOWED_PARAMETERS = frozenset({"pm25surf", "pm10surf", "o3surf", "no2surf"})
METADATA_CACHE_KEY = "geosphere_chem_v2_metadata"
TS_CACHE_KEY_PREFIX = "geosphere_chem_v2_ts_"
# Overlay uses the validity time nearest to UTC now + this many hours.
CHEM_FORECAST_TARGET_LEAD_HOURS = 24


def _parse_timestamp(iso_s: str) -> datetime:
    s = iso_s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def select_chem_forecast_hour_iso(timestamps: list[str]) -> str | None:
    """Pick the forecast validity timestamp closest to now + CHEM_FORECAST_TARGET_LEAD_HOURS."""
    if not timestamps:
        return None
    target = datetime.now(timezone.utc) + timedelta(
        hours=CHEM_FORECAST_TARGET_LEAD_HOURS
    )
    return min(
        timestamps,
        key=lambda t: abs((_parse_timestamp(t) - target).total_seconds()),
    )


def fetch_chem_metadata_cached() -> dict[str, Any] | None:
    cached = cache.get(METADATA_CACHE_KEY)
    if cached is not None:
        return cached
    url = (
        f"{settings.GEOSPHERE_DATASET_API_BASE.rstrip('/')}/grid/forecast/"
        f"{settings.GEOSPHERE_CHEM_FORECAST_RESOURCE_ID}/metadata"
    )
    try:
        resp = requests.get(url, timeout=settings.GEOSPHERE_API_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (RequestException, ValueError):
        return None
    cache.set(METADATA_CACHE_KEY, data, settings.GEOSPHERE_API_CACHE_TTL)
    return data


def fetch_chem_timestamps_cached(forecast_offset: int) -> list[str]:
    cache_key = f"{TS_CACHE_KEY_PREFIX}{forecast_offset}"
    cached = cache.get(cache_key)
    if isinstance(cached, list):
        return cached
    url = (
        f"{settings.GEOSPHERE_DATASET_API_BASE.rstrip('/')}/grid/forecast/"
        f"{settings.GEOSPHERE_CHEM_FORECAST_RESOURCE_ID}"
    )
    params = {
        "parameters": "pm25surf",
        "bbox": "48.2,16.3,48.21,16.31",
        "output_format": "geojson",
        "forecast_offset": forecast_offset,
    }
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=settings.GEOSPHERE_API_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (RequestException, ValueError):
        return []
    ts = data.get("timestamps")
    if not isinstance(ts, list):
        return []
    out = [str(x) for x in ts]
    cache.set(cache_key, out, settings.GEOSPHERE_API_CACHE_TTL)
    return out


def fetch_chem_grid_geojson(
    parameter: str,
    bbox: str,
    hour_iso: str,
    forecast_offset: int,
) -> dict[str, Any] | None:
    url = (
        f"{settings.GEOSPHERE_DATASET_API_BASE.rstrip('/')}/grid/forecast/"
        f"{settings.GEOSPHERE_CHEM_FORECAST_RESOURCE_ID}"
    )
    params = {
        "parameters": parameter,
        "bbox": bbox,
        "output_format": "geojson",
        "forecast_offset": forecast_offset,
        "start": hour_iso,
        "end": hour_iso,
    }
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=settings.GEOSPHERE_API_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except (RequestException, ValueError):
        return None
