from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from requests.exceptions import RequestException

from .views import HomePageView, LUFTDATEN_STATISTICS_REQUEST_TIMEOUT


class HomepageTests(SimpleTestCase):
    def setUp(self): # new
        url = reverse("home")
        self.response = self.client.get(url)
    
    def test_url_exists_at_correct_location(self):
        self.assertEqual(self.response.status_code, 200)

    def test_homepage_template(self):
        self.assertTemplateUsed(self.response, "home.html")

    def test_homepage_contains_correct_html(self):
        # Check for main content that should be present
        self.assertContains(self.response, 'Luftdaten.at Datahub')

    def test_homepage_does_not_contain_incorrect_html(self):
        self.assertNotContains(self.response, "Hi there! I should not be on the page.")

    def test_homepage_url_resolves_homepageview(self):
        view = resolve("/")
        self.assertEqual(view.func.__name__, HomePageView.as_view().__name__)


class LuftdatenStatisticsProxyTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    @patch("pages.views.requests.get")
    def test_proxy_returns_upstream_json(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "active_stations": {"last_hour": 42, "last_24_hours": 100},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        response = self.client.get(reverse("luftdaten_statistics_proxy"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["active_stations"]["last_hour"], 42)
        mock_get.assert_called_once()
        self.assertEqual(
            mock_get.call_args.kwargs["timeout"],
            LUFTDATEN_STATISTICS_REQUEST_TIMEOUT,
        )

    @patch("pages.views.requests.get")
    def test_proxy_uses_cache_second_request_skips_upstream(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = {"active_stations": {"last_hour": 1}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp
        url = reverse("luftdaten_statistics_proxy")

        self.client.get(url)
        self.client.get(url)

        mock_get.assert_called_once()

    @patch("pages.views.logger.warning")
    @patch("pages.views.requests.get")
    def test_proxy_returns_empty_active_stations_on_upstream_error(
        self, mock_get, mock_warning
    ):
        mock_get.side_effect = RequestException("upstream error")

        response = self.client.get(reverse("luftdaten_statistics_proxy"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"active_stations": {}})
        mock_warning.assert_called_once()
        fmt, err = mock_warning.call_args[0]
        self.assertEqual(fmt, "Luftdaten statistics proxy failed: %s")
        self.assertIn("upstream error", str(err))

    def test_proxy_url_resolves(self):
        self.assertEqual(
            reverse("luftdaten_statistics_proxy"),
            "/proxy/luftdaten-statistics/",
        )