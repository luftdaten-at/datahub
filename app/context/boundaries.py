"""Load boundary features from a GeoPackage and match municipalities."""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point

from .matching import NAME_MATCH_MAX_DISTANCE_DEG, normalize_municipality_name
from .models import Municipality


@dataclass
class BoundaryFeature:
    gkz: str
    name: str
    name_normalized: str
    geom: MultiPolygon
    area_km2: float | None
    population: int | None


def load_boundaries_from_gpkg(
    path: str,
    *,
    layer_name: str | None = None,
    gkz_field: str = "gkz",
    name_field: str = "name",
    area_field: str | None = "area_km2",
    population_field: str | None = "population",
) -> list[BoundaryFeature]:
    """Read municipality polygons from a GeoPackage."""
    ds = DataSource(path)
    layer = ds[layer_name] if layer_name else ds[0]
    features: list[BoundaryFeature] = []
    for feat in layer:
        gkz_raw = feat.get(gkz_field)
        name_raw = feat.get(name_field)
        if gkz_raw is None or name_raw is None:
            continue
        gkz = str(gkz_raw).strip().zfill(5)[:5]
        name = str(name_raw).strip()
        geom = feat.geom.geos
        if geom.geom_type == "Polygon":
            geom = MultiPolygon(geom, srid=geom.srid)
        elif geom.geom_type != "MultiPolygon":
            continue
        area_km2 = None
        if area_field and feat.get(area_field) is not None:
            try:
                area_km2 = float(feat.get(area_field))
            except (TypeError, ValueError):
                area_km2 = None
        population = None
        if population_field and feat.get(population_field) is not None:
            try:
                population = int(feat.get(population_field))
            except (TypeError, ValueError):
                population = None
        features.append(
            BoundaryFeature(
                gkz=gkz,
                name=name,
                name_normalized=normalize_municipality_name(name),
                geom=geom,
                area_km2=area_km2,
                population=population,
            )
        )
    return features


def _boundaries_containing_point(
    boundaries: list[BoundaryFeature], point: Point
) -> list[BoundaryFeature]:
    hits = []
    for b in boundaries:
        if b.geom.contains(point):
            hits.append(b)
    return hits


def _boundaries_by_name(
    boundaries: list[BoundaryFeature], name_normalized: str
) -> list[BoundaryFeature]:
    return [b for b in boundaries if b.name_normalized == name_normalized]


def match_municipality_to_boundary(
    municipality: Municipality,
    boundaries: list[BoundaryFeature],
) -> tuple[BoundaryFeature | None, str, float | None]:
    """
    Match one municipality to a boundary feature.

    Returns (boundary, match_method, confidence).
    """
    if municipality.centroid is None:
        return None, Municipality.MATCH_UNRESOLVED, None

    hits = _boundaries_containing_point(boundaries, municipality.centroid)
    if len(hits) == 1:
        return hits[0], Municipality.MATCH_AUTO, 1.0

    name_norm = normalize_municipality_name(municipality.name)
    candidates = _boundaries_by_name(boundaries, name_norm)
    if len(candidates) == 1:
        centroid = candidates[0].geom.centroid
        if municipality.centroid.distance(centroid) < NAME_MATCH_MAX_DISTANCE_DEG:
            return candidates[0], Municipality.MATCH_AUTO, 0.8

    return None, Municipality.MATCH_UNRESOLVED, None


def apply_boundary_match(
    municipality: Municipality,
    boundary: BoundaryFeature,
    *,
    match_method: str,
    confidence: float,
) -> None:
    municipality.gkz = boundary.gkz
    municipality.boundary = boundary.geom
    municipality.match_method = match_method
    municipality.match_confidence = confidence
    if boundary.area_km2 is not None:
        municipality.area_km2 = boundary.area_km2
    if boundary.population is not None:
        municipality.population = boundary.population
    municipality.save(
        update_fields=[
            "gkz",
            "boundary",
            "match_method",
            "match_confidence",
            "area_km2",
            "population",
            "synced_at",
        ]
    )


def match_all_municipalities(
    boundaries: list[BoundaryFeature],
) -> dict[str, int]:
    """Run matching for all municipalities. Returns counts by outcome."""
    counts = {"matched_pip": 0, "matched_name": 0, "unresolved": 0, "skipped": 0}
    for municipality in Municipality.objects.all():
        if municipality.match_method == Municipality.MATCH_MANUAL:
            counts["skipped"] += 1
            continue
        boundary, method, confidence = match_municipality_to_boundary(
            municipality, boundaries
        )
        if boundary is None:
            municipality.match_method = Municipality.MATCH_UNRESOLVED
            municipality.match_confidence = None
            municipality.save(update_fields=["match_method", "match_confidence", "synced_at"])
            counts["unresolved"] += 1
            continue
        apply_boundary_match(
            municipality,
            boundary,
            match_method=method,
            confidence=confidence,
        )
        if confidence == 1.0:
            counts["matched_pip"] += 1
        else:
            counts["matched_name"] += 1
    return counts
