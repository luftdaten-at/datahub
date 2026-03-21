import json
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse
from requests.exceptions import RequestException

from .models import FAQEntry
from .views import HelpPageView, HomePageView


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
            settings.LUFTDATEN_API_REQUEST_TIMEOUT,
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


class HelpPageTests(TestCase):
    def test_help_page_200(self):
        response = self.client.get(reverse("help"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "help.html")

    def test_help_empty_faq_message(self):
        response = self.client.get(reverse("help"))
        self.assertContains(
            response, "No questions have been published yet", html=False
        )

    def test_help_lists_published_faq_only(self):
        FAQEntry.objects.create(
            question="Public Q?",
            answer="Public A.",
            sort_order=1,
            is_published=True,
        )
        FAQEntry.objects.create(
            question="Draft Q",
            answer="Draft A",
            sort_order=0,
            is_published=False,
        )
        response = self.client.get(reverse("help"))
        self.assertContains(response, "Public Q?")
        self.assertContains(response, "Public A.")
        self.assertNotContains(response, "Draft Q")

    def test_help_url_resolves_helppageview(self):
        match = resolve("/help")
        self.assertEqual(match.func.view_class, HelpPageView)

    def test_help_staff_sees_unpublished_faq(self):
        User = get_user_model()
        staff = User.objects.create_user(
            username="faqstaff",
            email="faqstaff@example.com",
            password="secret",
            is_staff=True,
        )
        FAQEntry.objects.create(
            question="Public Q?",
            answer="Public A.",
            sort_order=0,
            is_published=True,
        )
        FAQEntry.objects.create(
            question="Draft Q",
            answer="Draft A",
            sort_order=1,
            is_published=False,
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("help"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Q?")
        self.assertContains(response, "Draft Q")


class FAQAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="apistaff",
            email="apistaff@example.com",
            password="secret",
            is_staff=True,
        )
        self.regular = User.objects.create_user(
            username="apiuser",
            email="apiuser@example.com",
            password="secret",
            is_staff=False,
        )

    def test_reorder_requires_staff(self):
        a = FAQEntry.objects.create(question="a", answer="a", sort_order=0)
        b = FAQEntry.objects.create(question="b", answer="b", sort_order=1)
        url = reverse("faq_api_reorder")
        body = json.dumps({"order": [b.pk, a.pk]})

        response = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.regular)
        response = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_reorder_staff_updates_sort_order(self):
        a = FAQEntry.objects.create(question="a", answer="a", sort_order=0)
        b = FAQEntry.objects.create(question="b", answer="b", sort_order=1)
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("faq_api_reorder"),
            data=json.dumps({"order": [b.pk, a.pk]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.sort_order, 1)
        self.assertEqual(b.sort_order, 0)

    def test_reorder_rejects_incomplete_id_list(self):
        FAQEntry.objects.create(question="a", answer="a", sort_order=0)
        b = FAQEntry.objects.create(question="b", answer="b", sort_order=1)
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("faq_api_reorder"),
            data=json.dumps({"order": [b.pk]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_staff(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("faq_api_create"),
            data=json.dumps(
                {
                    "question": "New?",
                    "answer": "Yes.",
                    "is_published": True,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["entry"]["question"], "New?")
        entry = FAQEntry.objects.get(pk=data["entry"]["id"])
        self.assertEqual(entry.updated_by, self.staff)

    def test_patch_staff(self):
        entry = FAQEntry.objects.create(
            question="Old?", answer="Old.", sort_order=0, is_published=True
        )
        self.client.force_login(self.staff)
        response = self.client.patch(
            reverse("faq_api_detail", kwargs={"pk": entry.pk}),
            data=json.dumps({"question": "New Q"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.question, "New Q")
        self.assertEqual(entry.updated_by, self.staff)

    def test_delete_staff(self):
        entry = FAQEntry.objects.create(question="x", answer="y", sort_order=0)
        self.client.force_login(self.staff)
        response = self.client.delete(
            reverse("faq_api_detail", kwargs={"pk": entry.pk}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FAQEntry.objects.filter(pk=entry.pk).exists())