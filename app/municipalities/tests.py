from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from municipalities.models import FavoriteMunicipality
from municipalities.city_registry import CITY_ALL_CACHE_KEY
from municipalities.views import (
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


def _city_current_response(name="Wien", slug="wien"):
    return {
        "type": "Feature",
        "geometry": {"coordinates": [16.37, 48.21]},
        "properties": {
            "name": name,
            "country": "AT",
            "timezone": "Europe/Vienna",
            "time": "2025-01-01T12:00:00Z",
            "station_count": 10,
            "values": [],
        },
    }


class MunicipalityDetailContextTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("municipalities.views.requests.get")
    def test_detail_renders_without_local_profile(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = _city_current_response()
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        r = self.client.get(reverse("municipalities-detail", kwargs={"pk": "wien"}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No Copernicus land indicators")
        self.assertContains(r, "No evaluable satellite heat data")

    @patch("municipalities.views.requests.get")
    def test_detail_shows_land_profile(self, mock_get):
        from context.models import Municipality, MunicipalityLandProfile
        from django.contrib.gis.geos import MultiPolygon, Point, Polygon

        ring = (
            (16.32, 48.16),
            (16.42, 48.16),
            (16.42, 48.26),
            (16.32, 48.26),
            (16.32, 48.16),
        )
        m = Municipality.objects.create(
            slug="wien",
            name="Wien",
            centroid=Point(16.37, 48.21, srid=4326),
            boundary=MultiPolygon(Polygon(ring), srid=4326),
            match_method=Municipality.MATCH_AUTO,
        )
        MunicipalityLandProfile.objects.create(
            municipality=m,
            reference_year=2021,
            imperviousness_pct=58.0,
            tree_cover_pct=22.0,
            data_source="urban_atlas",
            producer_version="1.0.0",
        )

        mock_resp = Mock()
        mock_resp.json.return_value = _city_current_response()
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        r = self.client.get(reverse("municipalities-detail", kwargs={"pk": "wien"}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "58.0")
        self.assertContains(r, "Environment")

    @patch("municipalities.views.requests.get")
    def test_detail_hides_heat_when_clear_fraction_low(self, mock_get):
        from context.models import Municipality, MunicipalityHeatProfile
        from django.contrib.gis.geos import MultiPolygon, Point, Polygon
        from datetime import datetime, timezone

        ring = (
            (16.32, 48.16),
            (16.42, 48.16),
            (16.42, 48.26),
            (16.32, 48.26),
            (16.32, 48.16),
        )
        m = Municipality.objects.create(
            slug="wien",
            name="Wien",
            centroid=Point(16.37, 48.21, srid=4326),
            boundary=MultiPolygon(Polygon(ring), srid=4326),
            match_method=Municipality.MATCH_AUTO,
        )
        MunicipalityHeatProfile.objects.create(
            municipality=m,
            reference_date="2026-06-29",
            acquisition_utc=datetime(2026, 6, 29, 9, 0, tzinfo=timezone.utc),
            sensor="LANDSAT_9",
            stac_item_id="x",
            clear_fraction=0.50,
            lst_mean=40.0,
            suhi_day=5.0,
            producer_version="1.0.0",
        )

        mock_resp = Mock()
        mock_resp.json.return_value = _city_current_response()
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        r = self.client.get(reverse("municipalities-detail", kwargs={"pk": "wien"}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No evaluable satellite heat data")
        self.assertNotContains(r, "Urban heat island (day)")


class ManageMunicipalityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="testpass123",
            is_staff=True,
        )
        self.regular = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="testpass123",
        )
        self.manage_url = reverse("municipalities-manage-list")
        self.sync_url = reverse("municipalities-manage-sync")

    def test_non_staff_get_manage_forbidden(self):
        self.client.login(username="user", password="testpass123")
        r = self.client.get(self.manage_url)
        self.assertEqual(r.status_code, 403)

    def test_staff_get_manage_ok(self):
        self.client.login(username="staff", password="testpass123")
        r = self.client.get(self.manage_url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "municipalities/manage/list.html")

    @patch("context.sync.sync_municipalities_from_api")
    def test_staff_post_sync_redirects_with_message(self, mock_sync):
        mock_sync.return_value = (2, 5, None)
        self.client.login(username="staff", password="testpass123")
        r = self.client.post(self.sync_url, follow=True)
        self.assertEqual(r.status_code, 200)
        mock_sync.assert_called_once()
        self.assertContains(r, "2 created")
        self.assertContains(r, "5 updated")

    @patch("context.sync.sync_municipalities_from_api")
    def test_staff_post_sync_shows_error(self, mock_sync):
        mock_sync.return_value = (0, 0, "API unavailable")
        self.client.login(username="staff", password="testpass123")
        r = self.client.post(self.sync_url, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "API unavailable")


class MunicipalitiesListLocalTests(TestCase):
    @patch("municipalities.views.requests.get")
    def test_public_list_uses_local_db_not_city_all(self, mock_get):
        from context.models import Municipality
        from django.contrib.gis.geos import Point

        Municipality.objects.create(
            slug="graz",
            name="Graz",
            country_code="AT",
            centroid=Point(15.44, 47.07, srid=4326),
        )

        r = self.client.get(reverse("municipalities-list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "municipality-list-data")
        self.assertContains(r, "Graz")
        self.assertContains(r, "graz")
        mock_get.assert_not_called()


class StaffNavbarTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staffnav",
            email="staffnav@test.com",
            password="testpass123",
            is_staff=True,
        )

    def test_staff_nav_shows_surveys_manage_link(self):
        self.client.login(username="staffnav", password="testpass123")
        r = self.client.get(reverse("municipalities-list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, reverse("surveys-manage-list"))
        self.assertContains(r, reverse("municipalities-manage-list"))
