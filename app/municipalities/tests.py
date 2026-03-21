from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from municipalities.models import FavoriteMunicipality


class FavoriteMunicipalityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="munifav",
            email="munifav@test.com",
            password="secret123",
        )
        self.client.login(username="munifav", password="secret123")

    @patch("municipalities.views.requests.get")
    def test_toggle_adds_then_removes(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "type": "Feature",
            "geometry": {"coordinates": [16.3, 48.2]},
            "properties": {
                "name": "Testburg",
                "country": "AT",
                "timezone": "Europe/Vienna",
                "time": "2025-01-01T12:00:00Z",
                "station_count": 3,
                "values": [],
            },
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        slug = "testburg"
        url_toggle = reverse("municipality-favorite-toggle", kwargs={"pk": slug})
        self.assertFalse(
            FavoriteMunicipality.objects.filter(
                user=self.user, municipality_slug=slug
            ).exists()
        )
        r = self.client.post(url_toggle)
        self.assertRedirects(
            r,
            reverse("municipalities-detail", kwargs={"pk": slug}),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            FavoriteMunicipality.objects.filter(
                user=self.user, municipality_slug=slug
            ).exists()
        )
        r2 = self.client.post(url_toggle)
        self.assertRedirects(
            r2,
            reverse("municipalities-detail", kwargs={"pk": slug}),
            fetch_redirect_response=False,
        )
        self.assertFalse(
            FavoriteMunicipality.objects.filter(
                user=self.user, municipality_slug=slug
            ).exists()
        )

    @patch("municipalities.views.requests.get")
    def test_detail_shows_remove_when_favorite(self, mock_get):
        slug = "wien"
        FavoriteMunicipality.objects.create(
            user=self.user, municipality_slug=slug
        )
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "type": "Feature",
            "geometry": {"coordinates": [16.37, 48.21]},
            "properties": {
                "name": "Wien",
                "country": "AT",
                "timezone": "Europe/Vienna",
                "time": "2025-01-01T12:00:00Z",
                "station_count": 10,
                "values": [],
            },
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        r = self.client.get(reverse("municipalities-detail", kwargs={"pk": slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Remove municipality from favourites")

    def test_anonymous_toggle_redirects_to_login(self):
        self.client.logout()
        url_toggle = reverse("municipality-favorite-toggle", kwargs={"pk": "foo"})
        r = self.client.post(url_toggle)
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r.url.lower())

    def test_legacy_cities_path_redirects(self):
        r = self.client.get("/cities/", follow=False)
        self.assertEqual(r.status_code, 301)
        self.assertTrue(r["Location"].endswith("/municipalities/"))

        r2 = self.client.get("/cities/wien/", follow=False)
        self.assertEqual(r2.status_code, 301)
        self.assertIn("/municipalities/wien", r2["Location"])
