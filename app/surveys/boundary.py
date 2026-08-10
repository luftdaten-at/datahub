"""Load survey boundaries from GeoJSON or GeoPackage."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point


class BoundaryLoadError(Exception):
    pass


def _to_multipolygon(geom: GEOSGeometry) -> MultiPolygon:
    if geom.geom_type == "Polygon":
        mp = MultiPolygon(geom, srid=geom.srid)
    elif geom.geom_type == "MultiPolygon":
        mp = geom
    else:
        raise BoundaryLoadError(
            f"Unsupported geometry type: {geom.geom_type}. Use Polygon or MultiPolygon."
        )
    if mp.srid and mp.srid != 4326:
        mp.transform(4326)
    elif not mp.srid:
        mp.srid = 4326
    return mp


def load_boundary_from_geojson(raw: bytes | str) -> MultiPolygon:
    try:
        if isinstance(raw, bytes):
            data = json.loads(raw.decode("utf-8"))
        else:
            data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundaryLoadError(f"Invalid GeoJSON: {exc}") from exc

    if data.get("type") == "FeatureCollection":
        geoms = []
        for feature in data.get("features", []):
            geom_data = feature.get("geometry")
            if geom_data:
                geoms.append(GEOSGeometry(json.dumps(geom_data)))
        if not geoms:
            raise BoundaryLoadError("FeatureCollection contains no geometries.")
        combined = geoms[0]
        for g in geoms[1:]:
            combined = combined.union(g)
        return _to_multipolygon(combined)
    if data.get("type") == "Feature":
        geom_data = data.get("geometry")
        if not geom_data:
            raise BoundaryLoadError("Feature has no geometry.")
        return _to_multipolygon(GEOSGeometry(json.dumps(geom_data)))
    if data.get("type") in ("Polygon", "MultiPolygon"):
        return _to_multipolygon(GEOSGeometry(json.dumps(data)))

    raise BoundaryLoadError("GeoJSON must be Feature, FeatureCollection, or geometry object.")


def load_boundary_from_gpkg(path: str, *, layer_name: str | None = None) -> MultiPolygon:
    ds = DataSource(path)
    layer = ds[layer_name] if layer_name else ds[0]
    geoms = []
    for feat in layer:
        geom = feat.geom.geos
        if geom.geom_type in ("Polygon", "MultiPolygon"):
            geoms.append(_to_multipolygon(geom))
    if not geoms:
        raise BoundaryLoadError("GeoPackage contains no polygon geometries.")
    combined = geoms[0]
    for g in geoms[1:]:
        combined = combined.union(g)
    return _to_multipolygon(combined)


def load_boundary_from_upload(uploaded_file) -> MultiPolygon:
    name = (uploaded_file.name or "").lower()
    if name.endswith((".geojson", ".json")):
        return load_boundary_from_geojson(uploaded_file.read())
    if name.endswith(".gpkg"):
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        try:
            return load_boundary_from_gpkg(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    raise BoundaryLoadError(
        "Unsupported file type. Upload .geojson, .json, or .gpkg."
    )


def point_in_boundary(lon: float, lat: float, boundary: MultiPolygon | None) -> bool:
    if boundary is None:
        return False
    point = Point(float(lon), float(lat), srid=4326)
    return boundary.contains(point)
