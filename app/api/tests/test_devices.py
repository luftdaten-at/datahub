"""Tests for device/station status and data endpoints."""
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from api.models import MobilityMode
from devices.models import Device, DeviceLogs
from workshops.models import Workshop, Participant


class StationStatusEndpointTest(TestCase):
    """POST api/v1/devices/status/ - add station status logs."""

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(
            id="STATUS001",
            api_key="secret-key-123",
            firmware="1.0",
            model=1,
        )
        self.valid_payload = {
            "station": {
                "device": self.device.id,
                "firmware": "1.0",
                "model": 1,
                "apikey": "secret-key-123",
                "battery": {"voltage": 3.7, "percentage": 80},
                "sensor_list": [{"model_id": 1, "dimension_list": [2, 3, 5]}],
            },
            "status_list": [
                {
                    "time": "2025-01-07T12:00:00Z",
                    "level": 1,
                    "message": "Test log entry",
                }
            ],
        }

    def test_station_status_missing_body_returns_400(self):
        response = self.client.post(
            reverse("api:v1:devices:station-status"),
            data={},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_station_status_valid_returns_200(self):
        response = self.client.post(
            reverse("api:v1:devices:station-status"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")
        self.assertTrue(DeviceLogs.objects.filter(device=self.device).exists())

    def test_station_status_wrong_api_key_returns_400(self):
        payload = {**self.valid_payload}
        payload["station"]["apikey"] = "wrong-key"
        response = self.client.post(
            reverse("api:v1:devices:station-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StationDataEndpointTest(TestCase):
    """POST api/v1/devices/data/ - add station measurement data (body: device, workshop, sensors)."""

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(
            id="DATA001",
            api_key="data-key-456",
            firmware="2.0",
            model=1,
        )
        self.workshop = Workshop.objects.create(
            title="Data Workshop",
            start_date="2025-01-01T00:00:00+00:00",
            end_date="2025-12-31T23:59:59+00:00",
        )
        self.participant = Participant.objects.create(
            name="8133a310-ffaf-11f0-8794-bbb756d19a96",
            workshop=self.workshop,
        )
        MobilityMode.objects.get_or_create(
            name="walking",
            defaults={"title": "Walking", "description": "On foot"},
        )
        self.valid_payload = {
            "device": {
                "time": "2025-01-07T11:23:23.439Z",
                "id": self.device.id,
                "firmware": "2.0",
                "model": 1,
                "apikey": "data-key-456",
            },
            "workshop": {
                "id": self.workshop.name,
                "participant": self.participant.name,
                "mode": "walking",
            },
            "sensors": {
                "1": {
                    "type": 1,
                    "data": {
                        "2": 5.0,
                        "3": 6.0,
                        "5": 7.0,
                        "6": 0.67,
                        "7": 20.0,
                    },
                },
            },
        }

    def test_station_data_missing_device_returns_400(self):
        response = self.client.post(
            reverse("api:v1:devices:station-data"),
            data={"workshop": {"id": "x", "participant": "y", "mode": "walking"}, "sensors": {}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_station_data_missing_workshop_returns_400(self):
        response = self.client.post(
            reverse("api:v1:devices:station-data"),
            data={
                "device": {"time": "2025-01-07T11:23:23Z", "id": "D1", "firmware": "1", "model": 1, "apikey": "k"},
                "sensors": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_station_data_valid_returns_200(self):
        response = self.client.post(
            reverse("api:v1:devices:station-data"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_station_data_wrong_api_key_returns_400(self):
        payload = {**self.valid_payload}
        payload["device"] = {**payload["device"], "apikey": "wrong-key"}
        response = self.client.post(
            reverse("api:v1:devices:station-data"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
