"""Tests for workshop spots add, delete, list endpoints."""
from django.contrib.gis.geos import Point
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser
from workshops.models import Workshop, WorkshopSpot


class WorkshopSpotAddEndpointTest(TestCase):
    """POST workshops/spot/add/ - requires auth and workshop owner."""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username="spotowner", email="owner@test.com", password="testpass123"
        )
        self.workshop = Workshop.objects.create(
            title="Spot Workshop",
            start_date="2020-01-01T00:00:00+00:00",
            end_date="2020-12-31T23:59:59+00:00",
            owner=self.user,
        )
        self.valid_payload = {
            "workshop": self.workshop.name,
            "lat": 48.21,
            "lon": 16.37,
            "radius": 100.0,
            "type": "hot",
        }

    def test_spot_add_unauthenticated_returns_401_or_403(self):
        response = self.client.post(
            reverse("api:v1:workshop-spot-add"),
            data=self.valid_payload,
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_spot_add_authenticated_returns_201(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("api:v1:workshop-spot-add"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(WorkshopSpot.objects.filter(workshop=self.workshop, type="hot").exists())


class WorkshopSpotDeleteEndpointTest(TestCase):
    """POST workshops/spot/delete/ - requires auth and workshop owner."""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username="delowner", email="del@test.com", password="testpass123"
        )
        self.workshop = Workshop.objects.create(
            title="Del Workshop",
            start_date="2020-01-01T00:00:00+00:00",
            end_date="2020-12-31T23:59:59+00:00",
            owner=self.user,
        )
        center = Point(16.37, 48.21, srid=4326)
        area = center.buffer(0.001)
        self.spot = WorkshopSpot.objects.create(
            workshop=self.workshop,
            center=center,
            radius=100.0,
            area=area,
            type="cool",
        )
        self.valid_payload = {
            "workshop": self.workshop.name,
            "workshop_spot": self.spot.pk,
        }

    def test_spot_delete_unauthenticated_returns_401_or_403(self):
        response = self.client.post(
            reverse("api:v1:workshop-spot-delete"),
            data=self.valid_payload,
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_spot_delete_authenticated_returns_200(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("api:v1:workshop-spot-delete"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(WorkshopSpot.objects.filter(pk=self.spot.pk).exists())


class WorkshopSpotListEndpointTest(TestCase):
    """GET workshops/<pk>/spot/ - list spots for a workshop."""

    def setUp(self):
        self.client = APIClient()
        self.workshop = Workshop.objects.create(
            title="List Workshop",
            start_date="2020-01-01T00:00:00+00:00",
            end_date="2020-12-31T23:59:59+00:00",
        )

    def test_spot_list_returns_200(self):
        response = self.client.get(
            reverse("api:v1:workshop-spot-list", kwargs={"pk": self.workshop.name})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), list)

    def test_spot_list_invalid_workshop_returns_400(self):
        response = self.client.get(
            reverse("api:v1:workshop-spot-list", kwargs={"pk": "nonexistent"})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
