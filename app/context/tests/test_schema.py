import json
from pathlib import Path

from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.test import TestCase
from jsonschema import Draft202012Validator

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"


class SchemaTests(TestCase):
    def _load(self, name):
        with open(FIXTURES / name, encoding="utf-8") as fh:
            return json.load(fh)

    def _validator(self, module):
        schema_file = SCHEMAS / f"{module}_profiles.v1.schema.json"
        with open(schema_file, encoding="utf-8") as fh:
            schema = json.load(fh)
        return Draft202012Validator(schema)

    def test_heat_valid_fixture(self):
        doc = self._load("heat_profiles_valid.json")
        errors = list(self._validator("heat").iter_errors(doc))
        self.assertEqual(errors, [])

    def test_land_valid_fixture(self):
        doc = self._load("land_profiles_valid.json")
        errors = list(self._validator("land").iter_errors(doc))
        self.assertEqual(errors, [])

    def test_schema_rejects_unknown_flag(self):
        doc = self._load("heat_profiles_unknown_flag.json")
        errors = list(self._validator("heat").iter_errors(doc))
        self.assertTrue(errors)

    def test_schema_rejects_bad_units(self):
        doc = self._load("heat_profiles_bad_units.json")
        errors = list(self._validator("heat").iter_errors(doc))
        self.assertTrue(errors)

    def test_schema_ignores_extra_fields(self):
        doc = self._load("heat_profiles_valid.json")
        doc["profiles"][0]["extra_future_field"] = 123
        errors = list(self._validator("heat").iter_errors(doc))
        self.assertEqual(errors, [])

    def test_schema_rejects_format_version_2(self):
        doc = self._load("heat_profiles_valid.json")
        doc["format_version"] = "2.0"
        errors = list(self._validator("heat").iter_errors(doc))
        self.assertTrue(errors)
