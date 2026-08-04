from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import TestCase

from context.models import Municipality
from context.sync import sync_municipalities_from_api


class SyncTests(TestCase):
    @patch("context.sync.load_city_registry_cities")
    def test_sync_creates_municipalities(self, mock_load):
        mock_load.return_value = (
            [
                {
                    "slug": "graz",
                    "name": "Graz",
                    "country_slug": "osterreich",
                    "latitude": 47.07,
                    "longitude": 15.44,
                }
            ],
            None,
        )
        created, updated, error = sync_municipalities_from_api()
        self.assertIsNone(error)
        self.assertEqual(created, 1)
        m = Municipality.objects.get(slug="graz")
        self.assertEqual(m.name, "Graz")
        self.assertEqual(m.country_code, "AT")
        self.assertAlmostEqual(m.centroid.x, 15.44)
        self.assertAlmostEqual(m.centroid.y, 47.07)

    @patch("context.sync.load_city_registry_cities")
    def test_sync_updates_existing(self, mock_load):
        Municipality.objects.create(slug="graz", name="Old Name")
        mock_load.return_value = (
            [
                {
                    "slug": "graz",
                    "name": "Graz",
                    "country_slug": "osterreich",
                    "latitude": 47.07,
                    "longitude": 15.44,
                }
            ],
            None,
        )
        created, updated, error = sync_municipalities_from_api()
        self.assertEqual(created, 0)
        self.assertEqual(updated, 1)
        self.assertEqual(Municipality.objects.get(slug="graz").name, "Graz")
