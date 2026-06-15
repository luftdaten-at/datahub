"""Tests for EAQI particulate-matter color bands."""
from django.test import SimpleTestCase

from main.eaqi_pm import PM1_COLOR_STEPS, PM10_COLOR_STEPS, PM25_COLOR_STEPS


class EaqiPmBandsTest(SimpleTestCase):
    def test_pm25_lower_bounds_match_eea_1h_bands(self):
        self.assertEqual([s[0] for s in PM25_COLOR_STEPS], [0, 6, 16, 51, 91, 141])

    def test_pm10_lower_bounds_match_eea_1h_bands(self):
        self.assertEqual([s[0] for s in PM10_COLOR_STEPS], [0, 16, 46, 121, 196, 271])

    def test_pm1_uses_pm25_bands(self):
        self.assertIs(PM1_COLOR_STEPS, PM25_COLOR_STEPS)

    def test_six_categories_each_pollutant(self):
        self.assertEqual(len(PM25_COLOR_STEPS), 6)
        self.assertEqual(len(PM10_COLOR_STEPS), 6)
