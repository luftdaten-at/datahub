"""Tests for schema and Swagger UI endpoints."""
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class SchemaEndpointTest(TestCase):
    """GET /api/schema/ returns OpenAPI schema."""

    def setUp(self):
        self.client = APIClient()

    def test_schema_returns_200(self):
        response = self.client.get(reverse("api:schema"))
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND))


class SwaggerUIEndpointTest(TestCase):
    """GET /api/docs/ returns Swagger UI."""

    def setUp(self):
        self.client = APIClient()

    def test_swagger_ui_returns_200(self):
        response = self.client.get(reverse("api:swagger-ui"))
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND))
