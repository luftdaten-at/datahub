"""Slug ↔ GKZ boundary matching helpers."""

from __future__ import annotations

import re
import unicodedata

from django.contrib.gis.geos import Point

# ~5 km at Austrian latitudes in degrees
NAME_MATCH_MAX_DISTANCE_DEG = 0.05

_UMLAUT_MAP = str.maketrans(
    {
        "ä": "a",
        "ö": "o",
        "ü": "u",
        "ß": "ss",
        "Ä": "a",
        "Ö": "o",
        "Ü": "u",
    }
)


def normalize_municipality_name(name: str) -> str:
    """Lowercase, strip accents/umlauts, collapse Sankt/St., remove punctuation."""
    if not name:
        return ""
    text = name.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.translate(_UMLAUT_MAP)
    text = re.sub(r"\bsankt\b", "st", text)
    text = re.sub(r"\bst\.\b", "st", text)
    text = re.sub(r"\ban der\b", "ad", text)
    text = re.sub(r"\ba\.\s*d\.\b", "ad", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def point_from_city(city: dict) -> Point | None:
    lat = city.get("latitude")
    lon = city.get("longitude")
    if lat is None or lon is None:
        return None
    try:
        return Point(float(lon), float(lat), srid=4326)
    except (TypeError, ValueError):
        return None
