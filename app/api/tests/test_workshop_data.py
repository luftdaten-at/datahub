"""Tests for workshop data add, detail, and workshop data GET endpoints."""
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from api.models import AirQualityRecord
from devices.models import Device
from workshops.models import Workshop


class WorkshopDataAddEndpointTest(TestCase):
    """POST workshop data add (v1) - add air quality records."""

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(id="B040")
        self.workshop = Workshop.objects.create(
            title="Test Workshop",
            start_date="2019-01-01T00:00:00+00:00",
            end_date="2019-12-31T23:59:59+00:00",
        )
        self.valid_payload = [
            {
                "time": "2019-01-01T00:00:00+00:00",
                "pm1": 10,
                "pm25": 20,
                "pm10": 30,
                "temperature": 20,
                "humidity": 50,
                "voc": 100,
                "nox": 200,
                "device": "B040",
                "workshop": self.workshop.name,
                "lat": 51.509865,
                "lon": -0.118092,
                "location_precision": 10,
            }
        ]
        self.invalid_payload = [{"pm1": 10, "pm25": 20}]

    def test_workshop_data_add_success(self):
        response = self.client.post(
            reverse("api:v1:workshop-data-add"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AirQualityRecord.objects.count(), 1)
        self.assertEqual(AirQualityRecord.objects.first().pm1, 10)

    def test_workshop_data_add_bad_request(self):
        response = self.client.post(
            reverse("api:v1:workshop-data-add"),
            data=self.invalid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WorkshopDetailEndpointTest(TestCase):
    """GET workshop detail by pk (v1)."""

    def setUp(self):
        self.client = APIClient()
        self.workshop = Workshop.objects.create(
            title="Detail Workshop",
            start_date="2020-01-01T00:00:00+00:00",
            end_date="2020-12-31T23:59:59+00:00",
        )

    def test_workshop_detail_returns_200(self):
        response = self.client.get(
            reverse("api:v1:workshop-detail", kwargs={"pk": self.workshop.name})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("name"), self.workshop.name)

    def test_workshop_detail_not_found(self):
        response = self.client.get(
            reverse("api:v1:workshop-detail", kwargs={"pk": "nonexistent"})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class WorkshopDataGetEndpointTest(TestCase):
    """GET workshops/<pk>/data/ - workshop air quality data."""

    def setUp(self):
        self.client = APIClient()
        self.workshop = Workshop.objects.create(
            title="Data Workshop",
            start_date="2020-01-01T00:00:00+00:00",
            end_date="2020-12-31T23:59:59+00:00",
        )

    def test_workshop_data_returns_200(self):
        response = self.client.get(
            reverse("api:v1:workshop-data", kwargs={"pk": self.workshop.name})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), list)

    def test_workshop_data_not_found(self):
        response = self.client.get(
            reverse("api:v1:workshop-data", kwargs={"pk": "nonexistent"})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
