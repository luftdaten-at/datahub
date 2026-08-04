from django.test import TestCase

from context.models import MunicipalityLandProfile, PeerGroup
from context.peer_groups import build_peer_groups
from context.tests.test_imports import _analysable_municipality


class PeerGroupTests(TestCase):
    def test_build_peer_groups_assigns_by_imperviousness(self):
        graz = _analysable_municipality("graz", "Graz", 15.45, 47.05)
        wien = _analysable_municipality("wien", "Wien", 16.37, 48.21)
        MunicipalityLandProfile.objects.create(
            municipality=graz,
            reference_year=2021,
            imperviousness_pct=20.0,
            data_source="urban_atlas",
            producer_version="1.0.0",
        )
        MunicipalityLandProfile.objects.create(
            municipality=wien,
            reference_year=2021,
            imperviousness_pct=55.0,
            data_source="urban_atlas",
            producer_version="1.0.0",
        )
        counts = build_peer_groups()
        self.assertEqual(PeerGroup.objects.count(), 3)
        self.assertEqual(counts["low_impervious"], 1)
        self.assertEqual(counts["high_impervious"], 1)
        self.assertEqual(
            MunicipalityLandProfile.objects.get(municipality=graz).peer_group.key,
            "low_impervious",
        )
