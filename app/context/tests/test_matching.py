from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.test import TestCase

from context.boundaries import (
    BoundaryFeature,
    match_municipality_to_boundary,
)
from context.matching import normalize_municipality_name
from context.models import Municipality


def _square_polygon(minx, miny, maxx, maxy):
    ring = ((minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy), (minx, miny))
    return MultiPolygon(Polygon(ring), srid=4326)


class MatchingTests(TestCase):
    def test_normalize_municipality_name(self):
        self.assertEqual(normalize_municipality_name("Sankt Pölten"), "st polten")
        self.assertEqual(normalize_municipality_name("Gröbming"), "grobming")

    def test_matching_point_in_polygon(self):
        boundary = BoundaryFeature(
            gkz="60101",
            name="Graz",
            name_normalized="graz",
            geom=_square_polygon(15.3, 47.0, 15.6, 47.1),
            area_km2=127.0,
            population=294630,
        )
        municipality = Municipality.objects.create(
            slug="graz",
            name="Graz",
            centroid=Point(15.45, 47.05, srid=4326),
        )
        matched, method, confidence = match_municipality_to_boundary(
            municipality, [boundary]
        )
        self.assertIsNotNone(matched)
        self.assertEqual(method, Municipality.MATCH_AUTO)
        self.assertEqual(confidence, 1.0)

    def test_matching_ambiguous_name(self):
        b1 = BoundaryFeature(
            gkz="10101",
            name="Neustift",
            name_normalized="neustift",
            geom=_square_polygon(16.0, 48.0, 16.1, 48.1),
            area_km2=50.0,
            population=5000,
        )
        b2 = BoundaryFeature(
            gkz="20202",
            name="Neustift",
            name_normalized="neustift",
            geom=_square_polygon(14.0, 47.0, 14.1, 47.1),
            area_km2=40.0,
            population=4000,
        )
        municipality = Municipality.objects.create(
            slug="neustift-x",
            name="Neustift",
            centroid=Point(15.0, 47.5, srid=4326),
        )
        matched, method, confidence = match_municipality_to_boundary(
            municipality, [b1, b2]
        )
        self.assertIsNone(matched)
        self.assertEqual(method, Municipality.MATCH_UNRESOLVED)
        self.assertIsNone(confidence)
