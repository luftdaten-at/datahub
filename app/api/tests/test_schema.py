"""Tests for schema and Swagger UI endpoints."""
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class SchemaEndpointTest(TestCase):
    """GET /api/v1/schema/ returns OpenAPI schema."""

    def setUp(self):
        self.client = APIClient()

    def test_schema_returns_200(self):
        response = self.client.get(reverse("api:v1:schema"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SwaggerUIEndpointTest(TestCase):
    """GET /api/v1/docs/ returns Swagger UI."""

    def setUp(self):
        self.client = APIClient()

    def test_swagger_ui_returns_200(self):
        response = self.client.get(reverse("api:v1:swagger-ui"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DocsRedirectTest(TestCase):
    """GET /api/docs/ redirects to /api/v1/docs/."""

    def setUp(self):
        self.client = APIClient()

    def test_docs_redirects(self):
        response = self.client.get("/api/docs/", follow=False)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("/api/v1/docs/", response["Location"])
