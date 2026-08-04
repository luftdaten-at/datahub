from datetime import datetime, timezone

from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.test import TestCase, override_settings

from context.models import (
    Municipality,
    MunicipalityHeatProfile,
    MunicipalityLandProfile,
    PeerGroup,
)
from context.services import get_municipality_context, lst_range, visible_metrics


def _analysable_municipality(slug, name, lon, lat):
    ring = (
        (lon - 0.05, lat - 0.05),
        (lon + 0.05, lat - 0.05),
        (lon + 0.05, lat + 0.05),
        (lon - 0.05, lat + 0.05),
        (lon - 0.05, lat - 0.05),
    )
    return Municipality.objects.create(
        slug=slug,
        name=name,
        centroid=Point(lon, lat, srid=4326),
        boundary=MultiPolygon(Polygon(ring), srid=4326),
        gkz="99999",
        match_method=Municipality.MATCH_AUTO,
        match_confidence=1.0,
    )


class ServicesTests(TestCase):
    def test_empty_context_for_unknown_slug(self):
        ctx = get_municipality_context("unknown")
        self.assertIsNone(ctx.land)
        self.assertFalse(ctx.heat_visible)

    def test_context_returns_bbox_and_boundary(self):
        _analysable_municipality("graz", "Graz", 15.45, 47.05)
        ctx = get_municipality_context("graz")
        self.assertIsNotNone(ctx.bbox)
        self.assertEqual(len(ctx.bbox), 4)
        self.assertIsNotNone(ctx.boundary_geojson)

    def test_heat_visible_requires_clear_fraction(self):
        m = _analysable_municipality("graz", "Graz", 15.45, 47.05)
        MunicipalityHeatProfile.objects.create(
            municipality=m,
            reference_date="2026-06-29",
            acquisition_utc=datetime(2026, 6, 29, 9, 47, 12, tzinfo=timezone.utc),
            sensor="LANDSAT_9",
            stac_item_id="x",
            clear_fraction=0.50,
            lst_mean=38.0,
            producer_version="1.0.0",
            quality_flags=[],
        )
        ctx = get_municipality_context("graz")
        self.assertFalse(ctx.heat_visible)
        self.assertIsNone(ctx.heat)

    @override_settings(CONTEXT_MIN_CLEAR_FRACTION=0.95)
    def test_weak_regression_hides_cooling_only(self):
        m = _analysable_municipality("graz", "Graz", 15.45, 47.05)
        heat = MunicipalityHeatProfile.objects.create(
            municipality=m,
            reference_date="2026-06-29",
            acquisition_utc=datetime(2026, 6, 29, 9, 47, 12, tzinfo=timezone.utc),
            sensor="LANDSAT_9",
            stac_item_id="x",
            clear_fraction=0.99,
            lst_mean=38.0,
            suhi_day=4.8,
            dlst_per_10pct_tcd=-2.4,
            producer_version="1.0.0",
            quality_flags=["weak_regression"],
        )
        metrics = visible_metrics(heat)
        self.assertTrue(metrics["suhi_day"])
        self.assertTrue(metrics["lst_stats"])
        self.assertFalse(metrics["cooling_regression"])

    def test_lst_range(self):
        m = _analysable_municipality("graz", "Graz", 15.45, 47.05)
        heat = MunicipalityHeatProfile.objects.create(
            municipality=m,
            reference_date="2026-06-29",
            acquisition_utc=datetime(2026, 6, 29, 9, 47, 12, tzinfo=timezone.utc),
            sensor="LANDSAT_9",
            stac_item_id="x",
            clear_fraction=0.99,
            lst_p10=30.0,
            lst_p90=46.0,
            producer_version="1.0.0",
        )
        self.assertAlmostEqual(lst_range(heat), 16.0)


class LandProfileContextTests(TestCase):
    def test_land_profile_in_context(self):
        m = _analysable_municipality("graz", "Graz", 15.45, 47.05)
        peer = PeerGroup.objects.create(
            key="low_impervious",
            label_de="Gering versiegelt",
            label_en="Low imperviousness",
        )
        MunicipalityLandProfile.objects.create(
            municipality=m,
            reference_year=2021,
            imperviousness_pct=42.5,
            tree_cover_pct=28.0,
            data_source="urban_atlas",
            producer_version="1.0.0",
            peer_group=peer,
        )
        ctx = get_municipality_context("graz")
        self.assertIsNotNone(ctx.land)
        self.assertEqual(ctx.peer_group.key, "low_impervious")
