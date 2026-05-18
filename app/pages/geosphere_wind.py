"""GeoSphere TAWES wind stations proxy (current 10 min observations)."""

from __future__ import annotations

from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from requests.exceptions import RequestException

TAUWES_METADATA_CACHE_KEY = "geosphere_tawes_v1_current_metadata"
TAUWES_WIND_GEOJSON_CACHE_KEY = "geosphere_tawes_v1_wind_geojson"


def fetch_tawes_metadata_cached() -> dict[str, Any] | None:
    cached = cache.get(TAUWES_METADATA_CACHE_KEY)
    if isinstance(cached, dict):
        return cached
    url = (
        f"{settings.GEOSPHERE_DATASET_API_BASE.rstrip('/')}/station/current/"
        f"{settings.GEOSPHERE_TAWES_RESOURCE_ID}/metadata"
    )
    try:
        resp = requests.get(url, timeout=settings.GEOSPHERE_API_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (RequestException, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    cache.set(
        TAUWES_METADATA_CACHE_KEY,
        data,
        settings.GEOSPHERE_TAWES_METADATA_CACHE_TTL,
    )
    return data


def _station_lookup(metadata: dict[str, Any]) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    stations = metadata.get("stations")
    if not isinstance(stations, list):
        return out
    for row in stations:
        if not isinstance(row, dict):
            continue
        sid = row.get("id")
        if sid is None:
            continue
        name = row.get("name") or ""
        state = row.get("state") or ""
        out[str(sid)] = (str(name), str(state))
    return out


def _enrich_wind_geojson(fc: dict[str, Any], metadata: dict[str, Any]) -> None:
    lookup = _station_lookup(metadata)
    features = fc.get("features")
    if not isinstance(features, list):
        return
    for feat in features:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties")
        if not isinstance(props, dict):
            props = {}
            feat["properties"] = props
        sid = str(props.get("station") or "")
        name, state = lookup.get(sid, ("", ""))
        props["station_name"] = name
        props["state"] = state


def fetch_tawes_wind_geojson_cached() -> dict[str, Any] | None:
    cached = cache.get(TAUWES_WIND_GEOJSON_CACHE_KEY)
    if isinstance(cached, dict):
        return cached

    metadata = fetch_tawes_metadata_cached()
    if metadata is None:
        return None

    stations = metadata.get("stations")
    if not isinstance(stations, list):
        return None
    ids = ",".join(
        str(s["id"])
        for s in stations
        if isinstance(s, dict) and s.get("is_active", True) and s.get("id") is not None
    )
    if not ids:
        return None

    url = (
        f"{settings.GEOSPHERE_DATASET_API_BASE.rstrip('/')}/station/current/"
        f"{settings.GEOSPHERE_TAWES_RESOURCE_ID}"
    )
    params = {
        "parameters": "FF,DD,FFX",
        "output_format": "geojson",
        "station_ids": ids,
    }
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=settings.GEOSPHERE_API_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        fc = resp.json()
    except (RequestException, ValueError):
        return None

    if not isinstance(fc, dict) or fc.get("type") != "FeatureCollection":
        return None

    _enrich_wind_geojson(fc, metadata)

    cache.set(
        TAUWES_WIND_GEOJSON_CACHE_KEY,
        fc,
        settings.GEOSPHERE_WIND_CACHE_TTL,
    )
    return fc
