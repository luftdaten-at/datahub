import json
from pathlib import Path

from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.test import TestCase, override_settings

from context.imports import accept, load_and_validate
from context.models import DatasetImport, Municipality, MunicipalityHeatProfile

FIXTURES = Path(__file__).resolve().parent / "fixtures"


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


class ImportTests(TestCase):
    def setUp(self):
        _analysable_municipality("graz", "Graz", 15.45, 47.05)
        _analysable_municipality("wien", "Wien", 16.37, 48.21)

    def _raw(self, name):
        return (FIXTURES / name).read_bytes()

    def test_import_valid_heat(self):
        result = load_and_validate(
            self._raw("heat_profiles_valid.json"),
            module="heat",
            filename="heat_profiles_valid.json",
        )
        self.assertTrue(result.ok, result.errors)
        accepted = accept(result.dataset_import)
        self.assertTrue(accepted.ok, accepted.errors)
        self.assertEqual(MunicipalityHeatProfile.objects.count(), 2)
        graz = MunicipalityHeatProfile.objects.get(municipality__slug="graz")
        self.assertAlmostEqual(graz.lst_mean, 38.4)

    def test_import_rejects_out_of_range(self):
        result = load_and_validate(
            self._raw("heat_profiles_bad_units.json"),
            module="heat",
            filename="heat_profiles_bad_units.json",
        )
        self.assertFalse(result.ok)

    def test_import_rejects_unknown_flag(self):
        result = load_and_validate(
            self._raw("heat_profiles_unknown_flag.json"),
            module="heat",
            filename="heat_profiles_unknown_flag.json",
        )
        self.assertFalse(result.ok)

    def test_import_rejects_inconsistent(self):
        doc = json.loads(self._raw("heat_profiles_valid.json"))
        doc["profiles"][0]["lst_p90"] = 20.0
        doc["profiles"][0]["lst_mean"] = 38.4
        raw = json.dumps(doc).encode()
        result = load_and_validate(raw, module="heat", filename="bad.json")
        self.assertFalse(result.ok)
        self.assertTrue(any("lst_mean" in e for e in result.errors))

    @override_settings(CONTEXT_IMPORT_MAX_LST_DELTA_K=15.0)
    def test_import_warns_on_large_delta(self):
        MunicipalityHeatProfile.objects.create(
            municipality=Municipality.objects.get(slug="graz"),
            reference_date="2025-07-14",
            acquisition_utc="2025-07-14T09:00:00Z",
            sensor="LANDSAT_9",
            stac_item_id="x",
            clear_fraction=0.99,
            lst_mean=22.0,
            producer_version="1.0.0",
        )
        result = load_and_validate(
            self._raw("heat_profiles_valid.json"),
            module="heat",
            filename="heat_profiles_valid.json",
        )
        self.assertTrue(result.ok, result.errors)
        self.assertTrue(any("deviates" in w for w in result.warnings))

    def test_import_idempotent(self):
        raw = self._raw("heat_profiles_valid.json")
        first = load_and_validate(raw, module="heat", filename="heat_profiles_valid.json")
        accept(first.dataset_import)
        second = load_and_validate(raw, module="heat", filename="heat_profiles_valid.json")
        self.assertTrue(second.ok)
        self.assertTrue(any("idempotent" in w.lower() for w in second.warnings))

    def test_import_pending_then_accept(self):
        result = load_and_validate(
            self._raw("heat_profiles_valid.json"),
            module="heat",
            filename="heat_profiles_valid.json",
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.dataset_import.status, DatasetImport.STATUS_PENDING)
        self.assertEqual(MunicipalityHeatProfile.objects.count(), 0)
        accepted = accept(result.dataset_import)
        self.assertTrue(accepted.ok)
        self.assertEqual(MunicipalityHeatProfile.objects.count(), 2)

    def test_import_land_valid(self):
        result = load_and_validate(
            self._raw("land_profiles_valid.json"),
            module="land",
            filename="land_profiles_valid.json",
        )
        self.assertTrue(result.ok, result.errors)
        accepted = accept(result.dataset_import)
        self.assertTrue(accepted.ok)
        self.assertEqual(accepted.dataset_import.profiles_written, 2)

    def test_dry_run_does_not_persist(self):
        result = load_and_validate(
            self._raw("heat_profiles_valid.json"),
            module="heat",
            filename="heat_profiles_valid.json",
            persist=False,
        )
        self.assertTrue(result.ok)
        self.assertIsNone(result.dataset_import)
        self.assertEqual(DatasetImport.objects.count(), 0)
