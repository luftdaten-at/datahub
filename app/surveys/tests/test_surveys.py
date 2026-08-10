import json

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from context.models import Municipality
from surveys.boundary import load_boundary_from_geojson, point_in_boundary
from surveys.models import MapPointCategory, MapPointAnswer, Survey, SurveyQuestion, SurveyResponse
from surveys.map_categories import sync_map_categories
from surveys.forms import normalize_question_config
from surveys.submit import SubmitError, validate_and_submit

User = get_user_model()


def _municipality(slug="graz", name="Graz"):
    ring = (
        (15.40, 47.00),
        (15.50, 47.00),
        (15.50, 47.10),
        (15.40, 47.10),
        (15.40, 47.00),
    )
    return Municipality.objects.create(
        slug=slug,
        name=name,
        centroid=Point(15.45, 47.05, srid=4326),
        boundary=MultiPolygon(Polygon(ring), srid=4326),
        match_method=Municipality.MATCH_AUTO,
    )


def _boundary_geojson():
    return json.dumps(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [15.40, 47.00],
                    [15.50, 47.00],
                    [15.50, 47.10],
                    [15.40, 47.10],
                    [15.40, 47.00],
                ]
            ],
        }
    ).encode()


def _survey(municipality, **kwargs):
    defaults = {
        "title": "Test Survey",
        "slug": "test-survey",
        "status": Survey.STATUS_DRAFT,
    }
    defaults.update(kwargs)
    survey = Survey.objects.create(municipality=municipality, **defaults)
    survey.boundary = load_boundary_from_geojson(_boundary_geojson())
    survey.save()
    return survey


def _map_question(survey, categories=None, point_choices=None, **kwargs):
    categories = categories or [{"key": "tree", "label": "Tree", "color": "#00aa00"}]
    config = {"max_points": 5, "categories": categories}
    if point_choices:
        config["point_choices"] = point_choices
    defaults = {
        "question_type": SurveyQuestion.TYPE_MAP_POINTS,
        "label": "Points",
        "required": True,
        "order": 0,
        "config": config,
    }
    defaults.update(kwargs)
    question = SurveyQuestion.objects.create(survey=survey, **defaults)
    sync_map_categories(question, categories)
    return question


class StaffAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user", password="pass")
        self.client = Client()

    def test_non_staff_forbidden(self):
        self.client.login(username="user", password="pass")
        r = self.client.get(reverse("surveys-manage-list"))
        self.assertEqual(r.status_code, 403)

    def test_staff_can_list(self):
        self.client.login(username="staff", password="pass")
        r = self.client.get(reverse("surveys-manage-list"))
        self.assertEqual(r.status_code, 200)


class BoundaryTests(TestCase):
    def test_point_in_boundary(self):
        mp = load_boundary_from_geojson(_boundary_geojson())
        self.assertTrue(point_in_boundary(15.45, 47.05, mp))
        self.assertFalse(point_in_boundary(16.0, 48.0, mp))


class SubmitTests(TestCase):
    def setUp(self):
        self.muni = _municipality()
        self.survey = _survey(self.muni, status=Survey.STATUS_PUBLISHED)
        self.text_q = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Comment",
            required=True,
            order=1,
        )
        self.range_q = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_RANGE,
            label="Rating",
            required=False,
            order=2,
            config={"min": 0, "max": 10},
        )
        self.map_q = _map_question(self.survey, order=3)
        self.category = self.map_q.map_categories.get(key="tree")

    def test_anonymous_submit(self):
        payload = {
            f"q_{self.text_q.id}": "Hello",
            f"q_{self.range_q.id}": "7",
            f"q_{self.map_q.id}": json.dumps(
                [
                    {
                        "lat": 47.05,
                        "lon": 15.45,
                        "category_id": self.category.id,
                        "comment": "Nice spot",
                    }
                ]
            ),
        }
        resp = validate_and_submit(self.survey, payload=payload)
        self.assertEqual(SurveyResponse.objects.count(), 1)
        self.assertEqual(resp.answers.count(), 2)
        self.assertEqual(resp.map_points.count(), 1)

    def test_point_outside_boundary_rejected(self):
        payload = {
            f"q_{self.text_q.id}": "Hello",
            f"q_{self.map_q.id}": json.dumps(
                [
                    {
                        "lat": 48.0,
                        "lon": 16.0,
                        "category_id": self.category.id,
                        "comment": "",
                    }
                ]
            ),
        }
        with self.assertRaises(SubmitError):
            validate_and_submit(self.survey, payload=payload)

    def test_draft_survey_rejected(self):
        self.survey.status = Survey.STATUS_DRAFT
        self.survey.save()
        with self.assertRaises(SubmitError):
            validate_and_submit(
                self.survey,
                payload={f"q_{self.text_q.id}": "x", f"q_{self.map_q.id}": "[]"},
            )


class PublicViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.muni = _municipality()
        self.survey = _survey(self.muni, status=Survey.STATUS_PUBLISHED)

    def test_public_list(self):
        r = self.client.get(reverse("surveys-list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Test Survey")

    def test_draft_not_public(self):
        self.survey.status = Survey.STATUS_DRAFT
        self.survey.save()
        r = self.client.get(reverse("surveys-detail", kwargs={"slug": self.survey.slug}))
        self.assertEqual(r.status_code, 404)

    def test_public_submit_via_post(self):
        text_q = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Name",
            required=True,
            order=1,
        )
        map_q = _map_question(self.survey, order=2)
        cat = map_q.map_categories.get(key="tree")
        r = self.client.post(
            reverse("surveys-submit", kwargs={"slug": self.survey.slug}),
            {
                f"q_{text_q.id}": "Test",
                f"q_{map_q.id}": json.dumps(
                    [{"lat": 47.05, "lon": 15.45, "category_id": cat.id, "comment": ""}]
                ),
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SurveyResponse.objects.count(), 1)


class StaffCreateSurveyTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.muni = _municipality()
        self.client = Client()
        self.client.login(username="staff", password="pass")

    def test_create_survey_with_boundary(self):
        geo = _boundary_geojson()
        r = self.client.post(
            reverse("surveys-manage-create"),
            {
                "municipality": self.muni.pk,
                "title": "Park Survey",
                "slug": "park-survey",
                "description": "Test",
                "boundary_file": SimpleUploadedFile(
                    "boundary.geojson", geo, content_type="application/geo+json"
                ),
            },
        )
        self.assertEqual(r.status_code, 302)
        survey = Survey.objects.get(slug="park-survey")
        self.assertIsNotNone(survey.boundary)

    def test_create_form_lists_api_synced_municipality(self):
        synced = Municipality.objects.create(
            slug="wien",
            name="Wien",
            country_code="AT",
            centroid=Point(16.37, 48.21, srid=4326),
            match_method=Municipality.MATCH_UNRESOLVED,
        )
        r = self.client.get(reverse("surveys-manage-create"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f'value="{synced.pk}"')
        self.assertContains(r, "Wien")

    def test_csv_export(self):
        survey = _survey(self.muni, slug="export-survey", status=Survey.STATUS_PUBLISHED)
        SurveyQuestion.objects.create(
            survey=survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Q1",
            order=1,
        )
        r = self.client.get(
            reverse("surveys-manage-responses-export", kwargs={"pk": survey.pk})
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])


class SurveyQuestionAPITests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffq", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="userq", password="pass")
        self.muni = _municipality()
        self.survey = _survey(self.muni, slug="api-survey")
        self.client = Client()

    def _create_url(self):
        return reverse("surveys-manage-questions-api", kwargs={"pk": self.survey.pk})

    def _detail_url(self, qid):
        return reverse(
            "surveys-manage-question-api",
            kwargs={"pk": self.survey.pk, "qid": qid},
        )

    def _reorder_url(self):
        return reverse("surveys-manage-questions-reorder", kwargs={"pk": self.survey.pk})

    def test_non_staff_forbidden(self):
        self.client.login(username="userq", password="pass")
        r = self.client.post(
            self._create_url(),
            data='{"question_type":"text","label":"Q1"}',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_create_update_delete_question(self):
        self.client.login(username="staffq", password="pass")
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "range",
                    "label": "How hot?",
                    "help_text": "0-10",
                    "required": True,
                    "config": {"min": 0, "max": 10},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        qid = r.json()["question"]["id"]
        self.assertEqual(r.json()["question"]["config"], {"min": 0.0, "max": 10.0})

        r2 = self.client.patch(
            self._detail_url(qid),
            data=json.dumps(
                {
                    "label": "Updated",
                    "config": {"min": 1, "max": 5},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["question"]["label"], "Updated")
        self.assertEqual(r2.json()["question"]["config"], {"min": 1.0, "max": 5.0})

        r3 = self.client.delete(self._detail_url(qid))
        self.assertEqual(r3.status_code, 200)
        self.assertFalse(SurveyQuestion.objects.filter(pk=qid).exists())

    def test_config_validation_rejects_invalid_range(self):
        self.client.login(username="staffq", password="pass")
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "range",
                    "label": "Bad range",
                    "config": {"min": 10, "max": 1},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("__all__", r.json()["errors"])

    def test_reorder_questions(self):
        q1 = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="First",
            order=0,
        )
        q2 = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Second",
            order=1,
        )
        self.client.login(username="staffq", password="pass")
        r = self.client.post(
            self._reorder_url(),
            data=json.dumps({"order": [q2.pk, q1.pk]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        q1.refresh_from_db()
        q2.refresh_from_db()
        self.assertEqual(q2.order, 0)
        self.assertEqual(q1.order, 1)

    def test_likert_and_map_config_persisted(self):
        self.client.login(username="staffq", password="pass")
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "likert",
                    "label": "Agree?",
                    "config": {"scale": 7},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["question"]["config"], {"scale": 7})

        r2 = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "map_points",
                    "label": "Mark spots",
                    "config": {
                        "max_points": 12,
                        "categories": [
                            {"key": "tree", "label": "Tree", "color": "#00aa00"}
                        ],
                    },
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r2.json()["question"]["config"]["max_points"], 12)
        self.assertEqual(len(r2.json()["question"]["config"]["categories"]), 1)
        qid = r2.json()["question"]["id"]
        question = SurveyQuestion.objects.get(pk=qid)
        self.assertEqual(question.map_categories.count(), 1)

    def test_map_question_requires_category(self):
        self.client.login(username="staffq", password="pass")
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "map_points",
                    "label": "No cats",
                    "config": {"max_points": 5, "categories": []},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)


class SurveySingleChoiceTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffchoice", password="pass", is_staff=True
        )
        self.muni = _municipality()
        self.survey = _survey(self.muni, slug="choice-survey", status=Survey.STATUS_PUBLISHED)
        self.client = Client()
        self.client.login(username="staffchoice", password="pass")

    def _create_url(self):
        return reverse("surveys-manage-questions-api", kwargs={"pk": self.survey.pk})

    def test_create_single_choice_persists_options(self):
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "single_choice",
                    "label": "Pick one",
                    "config": {"options": ["Yes", "No", "Maybe"]},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json()["question"]["config"],
            {"options": ["Yes", "No", "Maybe"]},
        )

    def test_create_single_choice_rejects_one_option(self):
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "single_choice",
                    "label": "Pick one",
                    "config": {"options": ["Only"]},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_submit_accepts_valid_choice(self):
        question = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_SINGLE_CHOICE,
            label="Color",
            required=True,
            order=0,
            config={"options": ["Red", "Blue"]},
        )
        resp = validate_and_submit(
            self.survey,
            payload={f"q_{question.id}": "Red"},
        )
        answer = resp.answers.get(question=question)
        self.assertEqual(answer.text_value, "Red")
        self.assertIsNone(answer.number_value)

    def test_submit_rejects_invalid_choice(self):
        question = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_SINGLE_CHOICE,
            label="Color",
            required=True,
            order=0,
            config={"options": ["Red", "Blue"]},
        )
        with self.assertRaises(SubmitError) as ctx:
            validate_and_submit(
                self.survey,
                payload={f"q_{question.id}": "Green"},
            )
        self.assertIn(f"q_{question.id}", ctx.exception.errors)

    def test_public_detail_shows_radio_inputs(self):
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_SINGLE_CHOICE,
            label="Color",
            required=True,
            order=0,
            config={"options": ["Red", "Blue"]},
        )
        r = self.client.get(reverse("surveys-detail", kwargs={"slug": self.survey.slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'type="radio"')
        self.assertContains(r, 'value="Red"')
        self.assertContains(r, 'value="Blue"')


class SurveyMultipleChoiceTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffmulti", password="pass", is_staff=True
        )
        self.muni = _municipality()
        self.survey = _survey(self.muni, slug="multi-choice-survey", status=Survey.STATUS_PUBLISHED)
        self.client = Client()
        self.client.login(username="staffmulti", password="pass")

    def _create_url(self):
        return reverse("surveys-manage-questions-api", kwargs={"pk": self.survey.pk})

    def test_create_multiple_choice_persists_options(self):
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "multiple_choice",
                    "label": "Pick many",
                    "config": {"options": ["A", "B", "C"]},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json()["question"]["config"],
            {"options": ["A", "B", "C"]},
        )

    def test_create_multiple_choice_rejects_one_option(self):
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "multiple_choice",
                    "label": "Pick many",
                    "config": {"options": ["Only"]},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_submit_accepts_multiple_valid_choices(self):
        question = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_MULTIPLE_CHOICE,
            label="Topics",
            required=True,
            order=0,
            config={"options": ["Air", "Noise", "Water"]},
        )
        resp = validate_and_submit(
            self.survey,
            payload={f"q_{question.id}": ["Air", "Water"]},
        )
        answer = resp.answers.get(question=question)
        self.assertEqual(json.loads(answer.text_value), ["Air", "Water"])
        self.assertIsNone(answer.number_value)

    def test_submit_rejects_invalid_choice(self):
        question = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_MULTIPLE_CHOICE,
            label="Topics",
            required=True,
            order=0,
            config={"options": ["Air", "Noise"]},
        )
        with self.assertRaises(SubmitError) as ctx:
            validate_and_submit(
                self.survey,
                payload={f"q_{question.id}": ["Air", "Light"]},
            )
        self.assertIn(f"q_{question.id}", ctx.exception.errors)

    def test_submit_required_empty_list_fails(self):
        question = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_MULTIPLE_CHOICE,
            label="Topics",
            required=True,
            order=0,
            config={"options": ["Air", "Noise"]},
        )
        with self.assertRaises(SubmitError) as ctx:
            validate_and_submit(
                self.survey,
                payload={f"q_{question.id}": []},
            )
        self.assertIn(f"q_{question.id}", ctx.exception.errors)

    def test_public_submit_via_post_with_checkboxes(self):
        question = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_MULTIPLE_CHOICE,
            label="Topics",
            required=True,
            order=0,
            config={"options": ["Air", "Noise", "Water"]},
        )
        r = self.client.post(
            reverse("surveys-submit", kwargs={"slug": self.survey.slug}),
            {
                f"q_{question.id}": ["Air", "Water"],
            },
        )
        self.assertEqual(r.status_code, 302)
        answer = SurveyResponse.objects.get().answers.get(question=question)
        self.assertEqual(json.loads(answer.text_value), ["Air", "Water"])

    def test_public_detail_shows_checkbox_inputs(self):
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_MULTIPLE_CHOICE,
            label="Topics",
            required=True,
            order=0,
            config={"options": ["Air", "Noise"]},
        )
        r = self.client.get(reverse("surveys-detail", kwargs={"slug": self.survey.slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'type="checkbox"')
        self.assertContains(r, 'value="Air"')
        self.assertContains(r, 'value="Noise"')


class SurveyEditPageTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffedit", password="pass", is_staff=True
        )
        self.muni = _municipality()
        self.survey = _survey(self.muni, slug="edit-survey")
        self.client = Client()
        self.client.login(username="staffedit", password="pass")

    def test_edit_page_has_questions_panel(self):
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Intro",
            order=0,
        )
        r = self.client.get(
            reverse("surveys-manage-edit", kwargs={"pk": self.survey.pk})
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "surveyQuestionsList")
        self.assertContains(r, "question-drag-handle")
        self.assertContains(r, "survey-questions-json")
        self.assertContains(r, "Intro")
        self.assertContains(r, "pageBreakAddBtn")
        self.assertContains(r, "Add page break")
        self.assertContains(r, "question-page-badge")
        self.assertContains(r, "surveyPagesSummary")

    def test_edit_page_shows_page_break_controls(self):
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Q1",
            order=0,
        )
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_PAGE_BREAK,
            label="Details",
            order=1,
        )
        r = self.client.get(
            reverse("surveys-manage-edit", kwargs={"pk": self.survey.pk})
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "question-page-break")
        self.assertContains(r, 'data-question-type="page_break"')
        self.assertContains(r, "Starts page")

    def test_old_questions_url_redirects_to_edit(self):
        r = self.client.get(
            reverse("surveys-manage-questions", kwargs={"pk": self.survey.pk})
        )
        self.assertRedirects(
            r,
            reverse("surveys-manage-edit", kwargs={"pk": self.survey.pk}),
            fetch_redirect_response=False,
        )


class SurveyMapQuestionCategoryTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffmapcat", password="pass", is_staff=True
        )
        self.muni = _municipality()
        self.survey = _survey(self.muni, slug="mapcat-survey")
        self.client = Client()
        self.client.login(username="staffmapcat", password="pass")

    def _create_url(self):
        return reverse("surveys-manage-questions-api", kwargs={"pk": self.survey.pk})

    def test_create_map_question_syncs_categories(self):
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "map_points",
                    "label": "Trees",
                    "config": {
                        "max_points": 10,
                        "categories": [
                            {"key": "tree", "label": "Tree", "color": "#00aa00"},
                        ],
                    },
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        qid = r.json()["question"]["id"]
        question = SurveyQuestion.objects.get(pk=qid)
        self.assertEqual(question.map_categories.count(), 1)
        self.assertEqual(question.map_categories.get().key, "tree")

    def test_create_map_question_rejects_multiple_categories(self):
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": "map_points",
                    "label": "Trees",
                    "config": {
                        "max_points": 10,
                        "categories": [
                            {"key": "tree", "label": "Tree", "color": "#00aa00"},
                            {"key": "bench", "label": "Bench", "color": "#aa0000"},
                        ],
                    },
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_categories_url_redirects_to_edit(self):
        r = self.client.get(
            reverse("surveys-manage-categories", kwargs={"pk": self.survey.pk})
        )
        self.assertRedirects(
            r,
            reverse("surveys-manage-edit", kwargs={"pk": self.survey.pk}),
        )


class SurveyStatusTransitionTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffstatus", password="pass", is_staff=True
        )
        self.muni = _municipality()
        self.survey = _survey(self.muni, slug="status-survey")
        self.client = Client()
        self.client.login(username="staffstatus", password="pass")
        self.edit_url = reverse("surveys-manage-edit", kwargs={"pk": self.survey.pk})

    def test_publish_redirects_to_edit_and_changes_status(self):
        r = self.client.post(
            reverse("surveys-manage-publish", kwargs={"pk": self.survey.pk})
        )
        self.assertRedirects(r, self.edit_url)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.status, Survey.STATUS_PUBLISHED)

    def test_publish_without_boundary_stays_draft(self):
        self.survey.boundary = None
        self.survey.save(update_fields=["boundary"])
        r = self.client.post(
            reverse("surveys-manage-publish", kwargs={"pk": self.survey.pk})
        )
        self.assertRedirects(r, self.edit_url)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.status, Survey.STATUS_DRAFT)

    def test_close_redirects_to_edit_and_changes_status(self):
        self.survey.status = Survey.STATUS_PUBLISHED
        self.survey.save(update_fields=["status"])
        r = self.client.post(
            reverse("surveys-manage-close", kwargs={"pk": self.survey.pk})
        )
        self.assertRedirects(r, self.edit_url)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.status, Survey.STATUS_CLOSED)

    def test_unpublish_redirects_to_edit_and_changes_status(self):
        self.survey.status = Survey.STATUS_PUBLISHED
        self.survey.save(update_fields=["status"])
        r = self.client.post(
            reverse("surveys-manage-unpublish", kwargs={"pk": self.survey.pk})
        )
        self.assertRedirects(r, self.edit_url)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.status, Survey.STATUS_DRAFT)

    def test_reopen_redirects_to_edit_and_changes_status(self):
        self.survey.status = Survey.STATUS_CLOSED
        self.survey.save(update_fields=["status"])
        r = self.client.post(
            reverse("surveys-manage-reopen", kwargs={"pk": self.survey.pk})
        )
        self.assertRedirects(r, self.edit_url)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.status, Survey.STATUS_PUBLISHED)

    def test_reopen_without_boundary_stays_closed(self):
        self.survey.status = Survey.STATUS_CLOSED
        self.survey.boundary = None
        self.survey.save(update_fields=["status", "boundary"])
        r = self.client.post(
            reverse("surveys-manage-reopen", kwargs={"pk": self.survey.pk})
        )
        self.assertRedirects(r, self.edit_url)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.status, Survey.STATUS_CLOSED)

    def test_edit_page_shows_status_actions(self):
        r = self.client.get(self.edit_url)
        self.assertContains(r, "Publish")

        self.survey.status = Survey.STATUS_PUBLISHED
        self.survey.save(update_fields=["status"])
        r = self.client.get(self.edit_url)
        self.assertContains(r, "Close survey")
        self.assertContains(r, "Unpublish")

        self.survey.status = Survey.STATUS_CLOSED
        self.survey.save(update_fields=["status"])
        r = self.client.get(self.edit_url)
        self.assertContains(r, "Reopen")


class SurveyPageBreakTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffpage", password="pass", is_staff=True
        )
        self.client = Client()
        self.muni = _municipality()
        self.survey = _survey(self.muni, slug="page-break-survey", status=Survey.STATUS_PUBLISHED)
        self.client.login(username="staffpage", password="pass")

    def _create_url(self):
        return reverse("surveys-manage-questions-api", kwargs={"pk": self.survey.pk})

    def test_create_page_break_via_api(self):
        r = self.client.post(
            self._create_url(),
            data=json.dumps(
                {
                    "question_type": SurveyQuestion.TYPE_PAGE_BREAK,
                    "label": "Page 2",
                    "required": True,
                    "config": {},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        question = r.json()["question"]
        self.assertEqual(question["question_type"], SurveyQuestion.TYPE_PAGE_BREAK)
        self.assertEqual(question["label"], "Page 2")
        self.assertFalse(question["required"])
        self.assertEqual(question["config"], {})

    def test_submit_with_page_break_succeeds(self):
        text_q = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Comment",
            required=True,
            order=0,
        )
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_PAGE_BREAK,
            label="Next page",
            order=1,
        )
        range_q = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_RANGE,
            label="Rating",
            required=False,
            order=2,
            config={"min": 0, "max": 10},
        )
        resp = validate_and_submit(
            self.survey,
            payload={
                f"q_{text_q.id}": "Hello",
                f"q_{range_q.id}": "5",
            },
        )
        self.assertEqual(resp.answers.count(), 2)

    def test_public_detail_has_pages_and_overview_map(self):
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="First",
            required=True,
            order=0,
        )
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_PAGE_BREAK,
            label="Details",
            order=1,
        )
        SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Second",
            required=False,
            order=2,
        )
        r = self.client.get(reverse("surveys-detail", kwargs={"slug": self.survey.slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.survey.title)
        self.assertContains(r, "survey-page")
        self.assertContains(r, "survey-boundary-overview")
        self.assertContains(r, "survey-page-nav")
        self.assertContains(r, "Details")
        self.assertContains(r, "col-lg-5")
        self.assertContains(r, "col-lg-7")
        self.assertNotContains(r, "survey-map-hint")
        self.assertNotContains(r, self.muni.name)

    def test_public_detail_shared_map_markup(self):
        _map_question(self.survey, order=0)
        r = self.client.get(reverse("surveys-detail", kwargs={"slug": self.survey.slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.survey.title)
        self.assertContains(r, "survey-boundary-overview")
        self.assertNotContains(r, "map-category-select")
        self.assertNotContains(r, 'class="survey-map mb-2"')
        self.assertNotContains(r, "survey-map-hint")
        self.assertContains(r, "Click on the map on the right")


class MapPointChoicesConfigTests(TestCase):
    def test_normalize_omits_point_choices_when_empty(self):
        config = normalize_question_config(
            SurveyQuestion.TYPE_MAP_POINTS,
            {
                "max_points": 10,
                "categories": [{"key": "tree", "label": "Tree", "color": "#00aa00"}],
            },
        )
        self.assertNotIn("point_choices", config)

    def test_normalize_accepts_point_choices(self):
        config = normalize_question_config(
            SurveyQuestion.TYPE_MAP_POINTS,
            {
                "max_points": 10,
                "categories": [{"key": "tree", "label": "Tree", "color": "#00aa00"}],
                "point_choices": {
                    "mode": "single",
                    "help_text": "Pick one",
                    "options": ["A", "B"],
                },
            },
        )
        self.assertEqual(config["point_choices"]["mode"], "single")
        self.assertEqual(config["point_choices"]["options"], ["A", "B"])
        self.assertEqual(config["point_choices"]["help_text"], "Pick one")


class MapPointChoicesSubmitTests(TestCase):
    def setUp(self):
        self.muni = _municipality()
        self.survey = _survey(self.muni, status=Survey.STATUS_PUBLISHED)
        self.text_q = SurveyQuestion.objects.create(
            survey=self.survey,
            question_type=SurveyQuestion.TYPE_TEXT,
            label="Comment",
            required=True,
            order=1,
        )
        self.map_q = _map_question(
            self.survey,
            order=2,
            point_choices={
                "mode": "single",
                "help_text": "What is here?",
                "options": ["Bench", "Tree"],
            },
        )
        self.category = self.map_q.map_categories.get(key="tree")

    def _base_payload(self, points):
        return {
            f"q_{self.text_q.id}": "Hello",
            f"q_{self.map_q.id}": json.dumps(points),
        }

    def test_submit_accepts_single_point_choice(self):
        payload = self._base_payload(
            [
                {
                    "lat": 47.05,
                    "lon": 15.45,
                    "category_id": self.category.id,
                    "comment": "",
                    "choices": ["Bench"],
                }
            ]
        )
        resp = validate_and_submit(self.survey, payload=payload)
        point = resp.map_points.get()
        self.assertEqual(point.choices, ["Bench"])

    def test_submit_rejects_missing_single_choice(self):
        payload = self._base_payload(
            [
                {
                    "lat": 47.05,
                    "lon": 15.45,
                    "category_id": self.category.id,
                    "comment": "",
                    "choices": [],
                }
            ]
        )
        with self.assertRaises(SubmitError) as ctx:
            validate_and_submit(self.survey, payload=payload)
        self.assertIn(f"q_{self.map_q.id}", ctx.exception.errors)

    def test_submit_rejects_invalid_choice(self):
        payload = self._base_payload(
            [
                {
                    "lat": 47.05,
                    "lon": 15.45,
                    "category_id": self.category.id,
                    "comment": "",
                    "choices": ["Unknown"],
                }
            ]
        )
        with self.assertRaises(SubmitError):
            validate_and_submit(self.survey, payload=payload)

    def test_submit_accepts_multiple_point_choices(self):
        self.map_q.config["point_choices"] = {
            "mode": "multiple",
            "options": ["Noise", "Smell", "Traffic"],
        }
        self.map_q.save(update_fields=["config"])
        payload = self._base_payload(
            [
                {
                    "lat": 47.05,
                    "lon": 15.45,
                    "category_id": self.category.id,
                    "comment": "",
                    "choices": ["Noise", "Traffic"],
                }
            ]
        )
        resp = validate_and_submit(self.survey, payload=payload)
        self.assertEqual(resp.map_points.get().choices, ["Noise", "Traffic"])


class MapPointChoicesStaffTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffchoices", password="pass", is_staff=True
        )
        self.muni = _municipality()
        self.survey = _survey(self.muni, slug="choices-survey")
        self.client = Client()
        self.client.login(username="staffchoices", password="pass")

    def test_create_map_question_with_point_choices(self):
        r = self.client.post(
            reverse("surveys-manage-questions-api", kwargs={"pk": self.survey.pk}),
            data=json.dumps(
                {
                    "question_type": "map_points",
                    "label": "Issues",
                    "config": {
                        "max_points": 10,
                        "categories": [
                            {"key": "issue", "label": "Issue", "color": "#ff0000"},
                        ],
                        "point_choices": {
                            "mode": "multiple",
                            "help_text": "Select all that apply",
                            "options": ["Noise", "Smell"],
                        },
                    },
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        question = SurveyQuestion.objects.get(pk=r.json()["question"]["id"])
        self.assertEqual(question.config["point_choices"]["mode"], "multiple")
        self.assertEqual(question.config["point_choices"]["options"], ["Noise", "Smell"])


class MapPointChoicesPublicTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.muni = _municipality()
        self.survey = _survey(self.muni, status=Survey.STATUS_PUBLISHED)

    def test_public_detail_includes_point_choices_in_map_config(self):
        _map_question(
            self.survey,
            order=0,
            point_choices={
                "mode": "single",
                "help_text": "What is here?",
                "options": ["Bench", "Tree"],
            },
        )
        r = self.client.get(reverse("surveys-detail", kwargs={"slug": self.survey.slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "point_choices")
        self.assertContains(r, "What is here?")
        self.assertContains(r, "survey-boundary-overview")
        self.assertContains(r, "No selection yet")
