"""
Resolve current PM2.5 for dashboard favourite cities/stations (Luftdaten API).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _

from main.enums import Dimension
from main.pm25_colors import pm25_to_rgb

logger = logging.getLogger(__name__)

PM25_DIMENSION = Dimension.PM2_5


def _parse_historical_pm25_by_device(payload: Any) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    if not isinstance(payload, list):
        return out
    for row in payload:
        dev = row.get("device")
        if dev is None:
            continue
        key = str(dev)
        values_obj: Dict[int, Any] = {}
        for item in row.get("values") or []:
            dim_raw = item.get("dimension")
            try:
                dim = int(dim_raw) if dim_raw is not None else None
            except (TypeError, ValueError):
                dim = None
            if dim is not None:
                values_obj[dim] = item.get("value")
        raw = values_obj.get(PM25_DIMENSION)
        try:
            out[key] = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            out[key] = None
    return out


def fetch_station_pm25_map(station_ids: List[str]) -> Dict[str, Optional[float]]:
    """Current PM2.5 per station id from /station/historical (end=current)."""
    if not station_ids:
        return {}
    url = f"{settings.API_URL}/station/historical"
    params = {
        "end": "current",
        "precision": "all",
        "output_format": "json",
        "station_ids": ",".join(str(s) for s in station_ids),
    }
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        by_dev = _parse_historical_pm25_by_device(resp.json())
    except (requests.RequestException, ValueError, TypeError) as e:
        logger.warning("Dashboard station PM2.5 fetch failed: %s", e)
        return {str(sid): None for sid in station_ids}
    return {str(sid): by_dev.get(str(sid)) for sid in station_ids}


def fetch_city_pm25_and_name(city_slug: str) -> Tuple[str, Optional[float]]:
    """GET /city/current — returns (display_name, pm25 or None)."""
    slug = str(city_slug).strip()
    url = f"{settings.API_URL}/city/current"
    params = {"city_slug": slug}
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError, TypeError) as e:
        logger.warning("Dashboard city PM2.5 fetch failed for %s: %s", slug, e)
        return slug, None

    properties = data.get("properties") or {}
    name = properties.get("name") or slug
    for item in properties.get("values") or []:
        dim_raw = item.get("dimension")
        try:
            dim = int(dim_raw) if dim_raw is not None else None
        except (TypeError, ValueError):
            dim = None
        if dim == PM25_DIMENSION:
            raw = item.get("value")
            try:
                return str(name), float(raw) if raw is not None else None
            except (TypeError, ValueError):
                return str(name), None
    return str(name), None


def build_favorite_station_rows(favorites) -> List[dict]:
    """favorites: queryset of FavoriteStation (ordered)."""
    ids = [f.station_id for f in favorites]
    pm_map = fetch_station_pm25_map(ids)
    rows = []
    for fav in favorites:
        sid = str(fav.station_id)
        pm = pm_map.get(sid)
        r, g, b = pm25_to_rgb(pm)
        rows.append(
            {
                "url": reverse("station-detail", kwargs={"pk": sid}),
                "label": f"{_('Station')} {sid}",
                "pm25": pm,
                "r": r,
                "g": g,
                "b": b,
            }
        )
    return rows


def build_favorite_city_rows(favorites) -> List[dict]:
    """favorites: queryset of FavoriteCity (ordered)."""
    rows = []
    for fav in favorites:
        slug = str(fav.city_slug)
        name, pm = fetch_city_pm25_and_name(slug)
        r, g, b = pm25_to_rgb(pm)
        rows.append(
            {
                "url": reverse("cities-detail", kwargs={"pk": slug}),
                "label": name,
                "pm25": pm,
                "r": r,
                "g": g,
                "b": b,
            }
        )
    return rows
