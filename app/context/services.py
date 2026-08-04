"""Read helpers and cache invalidation for municipality context profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache

from .models import Municipality, MunicipalityHeatProfile


@dataclass
class MunicipalityContext:
    land: object | None = None
    heat: object | None = None
    peer_group: object | None = None
    boundary_geojson: str | None = None
    bbox: list[float] | None = None
    tiles_url: str | None = None
    heat_visible: bool = False
    heat_metrics: dict[str, bool] = field(default_factory=dict)
    heat_lst_range: float | None = None
    heat_acquisition_local: str | None = None


def lst_range(heat: MunicipalityHeatProfile | None) -> float | None:
    if heat is None:
        return None
    if heat.lst_p90 is not None and heat.lst_p10 is not None:
        return heat.lst_p90 - heat.lst_p10
    if heat.lst_max is not None and heat.lst_p10 is not None:
        return heat.lst_max - heat.lst_p10
    return None


def visible_metrics(heat: MunicipalityHeatProfile | None) -> dict[str, bool]:
    if heat is None:
        return {}
    flags = set(heat.quality_flags or [])
    return {
        "suhi_day": heat.suhi_day is not None and "no_rural_reference" not in flags,
        "suhi_night": heat.suhi_night is not None and "no_rural_reference" not in flags,
        "cooling_regression": (
            (
                heat.dlst_per_10pct_tcd is not None
                or heat.dlst_per_10pct_imd is not None
            )
            and "weak_regression" not in flags
        ),
        "population": (
            heat.pop_in_hotspots is not None
            and heat.pop_total is not None
            and "population_suppressed" not in flags
        ),
        "lst_stats": heat.lst_mean is not None,
        "lst_by_landuse": bool(heat.lst_by_landuse),
    }


def _acquisition_local(heat: MunicipalityHeatProfile) -> str | None:
    if not heat.acquisition_utc:
        return None
    local = heat.acquisition_utc.astimezone(ZoneInfo("Europe/Vienna"))
    return local.strftime("%H:%M")


def get_municipality_context(slug: str) -> MunicipalityContext:
    cache_key = f"context_profile_{slug}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        municipality = (
            Municipality.objects.select_related(
                "land_profile",
                "land_profile__peer_group",
                "heat_profile",
            ).get(slug=slug)
        )
    except Municipality.DoesNotExist:
        return MunicipalityContext()

    heat = getattr(municipality, "heat_profile", None)
    heat_visible = bool(
        heat
        and heat.clear_fraction >= settings.CONTEXT_MIN_CLEAR_FRACTION
        and "insufficient_clear_pixels" not in (heat.quality_flags or [])
    )
    metrics = visible_metrics(heat if heat_visible else None)
    display_heat = heat if heat_visible else None

    ctx = MunicipalityContext(
        land=getattr(municipality, "land_profile", None),
        heat=display_heat,
        peer_group=getattr(
            getattr(municipality, "land_profile", None), "peer_group", None
        ),
        boundary_geojson=municipality.boundary.geojson if municipality.boundary else None,
        bbox=list(municipality.boundary.extent) if municipality.boundary else None,
        tiles_url=settings.CONTEXT_TILES_URL,
        heat_visible=heat_visible,
        heat_metrics=metrics,
        heat_lst_range=lst_range(display_heat),
        heat_acquisition_local=_acquisition_local(heat) if heat and heat_visible else None,
    )
    cache.set(cache_key, ctx, settings.CONTEXT_PROFILE_CACHE_TTL)
    return ctx


def invalidate_profile_cache_for_slugs(slugs: list[str]) -> None:
    for slug in slugs:
        cache.delete(f"context_profile_{slug}")
