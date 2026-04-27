from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from municipalities.models import FavoriteMunicipality
from municipalities.views import (
    CITY_ALL_CACHE_KEY,
    MunicipalitiesApiOverviewView,
    MunicipalityAdminLocationUpdateView,
)


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


class MunicipalitiesApiOverviewTests(TestCase):
    """Superuser-only overview of /city/all from api.luftdaten.at."""

    def setUp(self):
        cache.clear()
        self.url = reverse("municipalities-admin-overview")
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="testpass123",
        )
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="testpass123",
        )

    def tearDown(self):
        cache.clear()

    def test_url_resolves_to_correct_view(self):
        match = resolve("/municipalities/admin/overview/")
        self.assertEqual(
            match.func.__name__,
            MunicipalitiesApiOverviewView.as_view().__name__,
        )

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_regular_user_gets_403(self):
        self.client.login(username="user", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    @patch("municipalities.views.requests.get")
    def test_superuser_can_access_and_sees_city_from_api(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "cities": [
                {
                    "id": 99,
                    "name": "Teststadt",
                    "slug": "teststadt",
                    "location": {"latitude": 48.2, "longitude": 16.3},
                    "country": {"name": "Österreich", "slug": "osterreich"},
                }
            ]
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        self.client.login(username="admin", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "municipalities/admin_overview.html")
        self.assertContains(response, "Teststadt")
        self.assertContains(response, "teststadt")

    @patch("municipalities.views.requests.get")
    @override_settings(LUFTDATEN_ADMIN_API_KEY="admin-secret")
    def test_overview_shows_edit_when_admin_key_set(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "cities": [
                {
                    "id": 1,
                    "name": "Teststadt",
                    "slug": "teststadt",
                    "location": {"latitude": 48.2, "longitude": 16.3},
                    "country": {"name": "Österreich", "slug": "osterreich"},
                }
            ]
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        self.client.login(username="admin", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit location")


class MunicipalityAdminLocationUpdateTests(TestCase):
    def setUp(self):
        cache.clear()
        self.post_url = reverse("municipalities-admin-update-location")
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="testpass123",
        )
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="testpass123",
        )
        self._registry_row = {
            "id": 1,
            "name": "Teststadt",
            "slug": "teststadt",
            "country_name": "Österreich",
            "country_slug": "osterreich",
            "latitude": 48.2,
            "longitude": 16.3,
            "country_filter": "osterreich",
        }

    def tearDown(self):
        cache.clear()

    def test_resolve(self):
        match = resolve("/municipalities/admin/update-location/")
        self.assertEqual(
            match.func.__name__,
            MunicipalityAdminLocationUpdateView.as_view().__name__,
        )

    def test_regular_user_post_forbidden(self):
        cache.set(CITY_ALL_CACHE_KEY, [self._registry_row])
        self.client.login(username="user", password="testpass123")
        r = self.client.post(
            self.post_url,
            {
                "city_slug": "teststadt",
                "latitude": "48.3",
                "longitude": "16.4",
            },
        )
        self.assertEqual(r.status_code, 403)

    @override_settings(LUFTDATEN_ADMIN_API_KEY="")
    def test_missing_admin_key_shows_error(self):
        cache.set(CITY_ALL_CACHE_KEY, [self._registry_row])
        self.client.login(username="admin", password="testpass123")
        r = self.client.post(
            self.post_url,
            {
                "city_slug": "teststadt",
                "latitude": "48.3",
                "longitude": "16.4",
            },
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(
            r, "Luftdaten admin API key is not configured on this server."
        )

    @patch("municipalities.luftdaten_city_admin.requests.post")
    @patch("municipalities.views.requests.get")
    @override_settings(LUFTDATEN_ADMIN_API_KEY="admin-secret")
    def test_superuser_post_calls_city_admin_and_clears_cache(
        self, mock_views_get, mock_admin_post
    ):
        cache.set(CITY_ALL_CACHE_KEY, [self._registry_row])

        cur = Mock()
        cur.json.return_value = {
            "properties": {"timezone": "Europe/Vienna"},
        }
        cur.raise_for_status = Mock()

        def views_get(url, **kwargs):
            if "city/current" in url:
                return cur
            raise AssertionError("unexpected GET " + url)

        mock_views_get.side_effect = views_get

        post_resp = Mock()
        post_resp.status_code = 200
        post_resp.json.return_value = {}
        mock_admin_post.return_value = post_resp

        self.client.login(username="admin", password="testpass123")
        r = self.client.post(
            self.post_url,
            {
                "city_slug": "teststadt",
                "latitude": "48.333",
                "longitude": "16.444",
            },
        )
        self.assertRedirects(
            r,
            reverse("municipalities-admin-overview"),
            fetch_redirect_response=False,
        )
        self.assertIsNone(cache.get(CITY_ALL_CACHE_KEY))
        mock_admin_post.assert_called_once()
        call_kw = mock_admin_post.call_args.kwargs
        self.assertIn("json", call_kw)
        body = call_kw["json"]
        self.assertEqual(body["slug"], "teststadt")
        self.assertEqual(body["name"], "Teststadt")
        self.assertEqual(body["tz"], "Europe/Vienna")
        self.assertEqual(body["lat"], 48.333)
        self.assertEqual(body["lon"], 16.444)
        self.assertEqual(body["country_code"], "AT")
        headers = call_kw.get("headers") or mock_admin_post.call_args[1].get("headers")
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Bearer "))
