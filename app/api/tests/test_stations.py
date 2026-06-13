"""Tests for station API endpoints."""
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from devices.models import Device
from main.enums import LdProduct


class StationNameEndpointTest(TestCase):
    """GET /api/v1/stations/name/ - resolve device name by id."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("api:v1:station-name")
        self.device = Device.objects.create(
            id="D83BDA6E37DDAAA",
            device_name="Air Cube 0042",
            model=LdProduct.AIR_CUBE,
            auto_number=42,
        )
        self.air_station = Device.objects.create(
            id="123456789012345",
            model=LdProduct.AIR_STATION,
            auto_number=7,
        )

    def test_returns_device_name_for_full_id(self):
        response = self.client.get(self.url, {"device": self.device.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["device"], self.device.id)
        self.assertEqual(response.data["device_name"], "Air Cube 0042")

    def test_missing_device_param_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("device", response.data)

    def test_unknown_device_returns_404(self):
        response = self.client.get(self.url, {"device": "UNKNOWN000000000"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_air_station_short_auto_number(self):
        response = self.client.get(self.url, {"device": "7"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["device"], self.air_station.id)
        self.assertEqual(response.data["device_name"], "Station 7")

    def test_fallback_to_device_id_when_name_empty(self):
        bare = Device.objects.create(id="AAAAAAAAAAAAAAA")
        response = self.client.get(self.url, {"device": bare.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["device_name"], bare.id)
