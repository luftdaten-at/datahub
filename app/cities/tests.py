from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cities.models import FavoriteCity


class FavoriteCityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="cityfav",
            email="cityfav@test.com",
            password="secret123",
        )
        self.client.login(username="cityfav", password="secret123")

    @patch("cities.views.requests.get")
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
        url_toggle = reverse("city-favorite-toggle", kwargs={"pk": slug})
        self.assertFalse(
            FavoriteCity.objects.filter(user=self.user, city_slug=slug).exists()
        )
        r = self.client.post(url_toggle)
        self.assertRedirects(
            r,
            reverse("cities-detail", kwargs={"pk": slug}),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            FavoriteCity.objects.filter(user=self.user, city_slug=slug).exists()
        )
        r2 = self.client.post(url_toggle)
        self.assertRedirects(
            r2,
            reverse("cities-detail", kwargs={"pk": slug}),
            fetch_redirect_response=False,
        )
        self.assertFalse(
            FavoriteCity.objects.filter(user=self.user, city_slug=slug).exists()
        )

    @patch("cities.views.requests.get")
    def test_detail_shows_remove_when_favorite(self, mock_get):
        slug = "wien"
        FavoriteCity.objects.create(user=self.user, city_slug=slug)
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

        r = self.client.get(reverse("cities-detail", kwargs={"pk": slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Remove city from favourites")

    def test_anonymous_toggle_redirects_to_login(self):
        self.client.logout()
        url_toggle = reverse("city-favorite-toggle", kwargs={"pk": "foo"})
        r = self.client.post(url_toggle)
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r.url.lower())
