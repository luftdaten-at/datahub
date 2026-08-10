import csv
import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Max
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .boundary import BoundaryLoadError, load_boundary_from_upload
from .forms import SurveyForm, SurveyQuestionForm
from .map_categories import sync_map_categories
from .models import Survey, SurveyQuestion, SurveyResponse
from .submit import SubmitError, validate_and_submit


def _question_json(question):
    config = dict(question.config or {})
    if question.question_type == SurveyQuestion.TYPE_MAP_POINTS:
        db_categories = list(question.map_categories.order_by("order", "id"))
        if db_categories:
            config["categories"] = [_category_json(c) for c in db_categories]
    return {
        "id": question.id,
        "question_type": question.question_type,
        "question_type_display": question.get_question_type_display(),
        "label": question.label,
        "help_text": question.help_text,
        "required": question.required,
        "order": question.order,
        "config": config,
    }


def _build_survey_pages(questions):
    pages = []
    current_title = ""
    current_questions = []
    for question in questions:
        if question.question_type == SurveyQuestion.TYPE_PAGE_BREAK:
            if current_questions:
                pages.append({"title": current_title, "questions": current_questions})
                current_questions = []
            current_title = question.label
        else:
            current_questions.append(question)
    if current_questions:
        pages.append({"title": current_title, "questions": current_questions})
    return pages


def _questions_with_page_numbers(questions):
    """Annotate each question with the public form page number it belongs to."""
    page = 1
    annotated = []
    for question in questions:
        if question.question_type == SurveyQuestion.TYPE_PAGE_BREAK:
            page += 1
        question.page_number = page
        annotated.append(question)
    return annotated, page


def _category_json(category):
    return {
        "id": category.id,
        "key": category.key,
        "label": category.label,
        "color": category.color,
        "order": category.order,
    }


def _parse_json_body(request):
    try:
        data = json.loads(request.body.decode() or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class ManageSurveyListView(StaffRequiredMixin, ListView):
    model = Survey
    template_name = "surveys/manage/list.html"
    context_object_name = "surveys"
    paginate_by = 25


class ManageSurveyCreateView(StaffRequiredMixin, CreateView):
    model = Survey
    form_class = SurveyForm
    template_name = "surveys/manage/form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.status = Survey.STATUS_DRAFT
        response = super().form_valid(form)
        boundary_file = form.cleaned_data.get("boundary_file")
        if boundary_file:
            try:
                self.object.boundary = load_boundary_from_upload(boundary_file)
                self.object.save(update_fields=["boundary"])
            except BoundaryLoadError as exc:
                messages.warning(
                    self.request,
                    _("Boundary not loaded: %(error)s") % {"error": exc},
                )
        messages.success(self.request, _("Survey created."))
        return response

    def get_success_url(self):
        return reverse("surveys-manage-edit", kwargs={"pk": self.object.pk})


class ManageSurveyUpdateView(StaffRequiredMixin, UpdateView):
    model = Survey
    form_class = SurveyForm
    template_name = "surveys/manage/form.html"
    context_object_name = "survey"

    def form_valid(self, form):
        response = super().form_valid(form)
        boundary_file = form.cleaned_data.get("boundary_file")
        if boundary_file:
            try:
                self.object.boundary = load_boundary_from_upload(boundary_file)
                self.object.save(update_fields=["boundary"])
                messages.success(self.request, _("Boundary updated."))
            except BoundaryLoadError as exc:
                messages.error(self.request, str(exc))
                return self.form_invalid(form)
        messages.success(self.request, _("Survey saved."))
        return response

    def get_success_url(self):
        return reverse("surveys-manage-edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questions = list(
            self.object.questions.prefetch_related("map_categories").order_by("order", "id")
        )
        questions, page_count = _questions_with_page_numbers(questions)
        context["questions"] = questions
        context["question_page_count"] = page_count if questions else 0
        context["questions_json"] = [_question_json(q) for q in questions]
        context["question_type_choices"] = SurveyQuestion.TYPE_CHOICES
        context["question_api_detail_placeholder_pk"] = 987654321
        return context


class ManageSurveyQuestionsView(StaffRequiredMixin, View):
    def get(self, request, pk):
        return redirect("surveys-manage-edit", pk=pk)

    def post(self, request, pk):
        return redirect("surveys-manage-edit", pk=pk)


class ManageSurveyQuestionsAPIView(StaffRequiredMixin, View):
    def post(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk)
        data = _parse_json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        max_order = survey.questions.aggregate(m=Max("order"))["m"]
        next_order = (max_order + 1) if max_order is not None else 0

        form = SurveyQuestionForm(
            {
                "question_type": data.get("question_type", ""),
                "label": data.get("label", ""),
                "help_text": data.get("help_text", ""),
                "required": data.get("required", False),
                "order": data.get("order", next_order),
            },
            config=data.get("config"),
        )
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)

        question = form.save(commit=False)
        question.survey = survey
        if question.order is None:
            question.order = next_order
        question.save()
        if question.question_type == SurveyQuestion.TYPE_MAP_POINTS:
            try:
                sync_map_categories(question, form.cleaned_data["config"]["categories"])
            except ValidationError as exc:
                question.delete()
                return JsonResponse({"errors": {"__all__": exc.messages}}, status=400)
        question.refresh_from_db()
        return JsonResponse({"ok": True, "question": _question_json(question)}, status=201)


class ManageSurveyQuestionAPIView(StaffRequiredMixin, View):
    def get_question(self, pk, qid):
        return get_object_or_404(SurveyQuestion, pk=qid, survey_id=pk)

    def get(self, request, pk, qid):
        question = self.get_question(pk, qid)
        return JsonResponse({"ok": True, "question": _question_json(question)})

    def patch(self, request, pk, qid):
        question = self.get_question(pk, qid)
        data = _parse_json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        payload = {
            "question_type": data.get("question_type", question.question_type),
            "label": data.get("label", question.label),
            "help_text": data.get("help_text", question.help_text),
            "required": data.get("required", question.required),
            "order": data.get("order", question.order),
        }
        config = data.get("config", question.config)

        form = SurveyQuestionForm(payload, instance=question, config=config)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)

        question = form.save()
        if question.question_type == SurveyQuestion.TYPE_MAP_POINTS:
            try:
                sync_map_categories(question, form.cleaned_data["config"]["categories"])
            except ValidationError as exc:
                return JsonResponse({"errors": {"__all__": exc.messages}}, status=400)
        question.refresh_from_db()
        return JsonResponse({"ok": True, "question": _question_json(question)})

    def delete(self, request, pk, qid):
        question = self.get_question(pk, qid)
        question.delete()
        return JsonResponse({"ok": True})


class ManageSurveyQuestionsReorderView(StaffRequiredMixin, View):
    def post(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk)
        data = _parse_json_body(request)
        if data is None:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        order = data.get("order")
        if not isinstance(order, list):
            return JsonResponse({"error": "order must be a list"}, status=400)
        try:
            order_ids = [int(x) for x in order]
        except (TypeError, ValueError):
            return JsonResponse({"error": "order must contain integers"}, status=400)

        survey_ids = set(survey.questions.values_list("pk", flat=True))
        if set(order_ids) != survey_ids or len(order_ids) != len(survey_ids):
            return JsonResponse(
                {"error": "order must list each question id exactly once"},
                status=400,
            )

        with transaction.atomic():
            for index, qid in enumerate(order_ids):
                SurveyQuestion.objects.filter(pk=qid, survey=survey).update(order=index)

        return JsonResponse({"ok": True})


class ManageSurveyCategoriesView(StaffRequiredMixin, View):
    def get(self, request, pk):
        return redirect("surveys-manage-edit", pk=pk)

    def post(self, request, pk):
        return redirect("surveys-manage-edit", pk=pk)


class ManageSurveyResponsesView(StaffRequiredMixin, DetailView):
    model = Survey
    template_name = "surveys/manage/responses.html"
    context_object_name = "survey"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["responses"] = (
            self.object.responses.select_related("user")
            .prefetch_related("answers__question", "map_points__category")
            .all()[:200]
        )
        return context


class ManageSurveyResponsesExportView(StaffRequiredMixin, View):
    def get(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="survey_{survey.slug}_responses.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                "response_id",
                "submitted_at",
                "user",
                "anonymous_key",
                "question_id",
                "question_label",
                "text_value",
                "number_value",
                "map_lat",
                "map_lon",
                "category",
                "comment",
            ]
        )
        for resp in survey.responses.prefetch_related(
            "answers__question", "map_points__category"
        ).all():
            for answer in resp.answers.all():
                writer.writerow(
                    [
                        resp.pk,
                        resp.submitted_at.isoformat(),
                        resp.user.username if resp.user else "",
                        resp.anonymous_key,
                        answer.question_id,
                        answer.question.label,
                        answer.text_value,
                        answer.number_value,
                        "",
                        "",
                        "",
                        "",
                    ]
                )
            for pt in resp.map_points.all():
                writer.writerow(
                    [
                        resp.pk,
                        resp.submitted_at.isoformat(),
                        resp.user.username if resp.user else "",
                        resp.anonymous_key,
                        pt.question_id,
                        pt.question.label,
                        "",
                        "",
                        pt.location.y,
                        pt.location.x,
                        pt.category.label,
                        pt.comment,
                    ]
                )
        return response


class ManageSurveyPublishView(StaffRequiredMixin, View):
    def post(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk)
        if survey.status != Survey.STATUS_DRAFT:
            return redirect("surveys-manage-edit", pk=pk)
        if not survey.boundary:
            messages.error(request, _("Upload a boundary before publishing."))
            return redirect("surveys-manage-edit", pk=pk)
        survey.status = Survey.STATUS_PUBLISHED
        survey.save(update_fields=["status", "updated_at"])
        messages.success(request, _("Survey published."))
        return redirect("surveys-manage-edit", pk=pk)


class ManageSurveyCloseView(StaffRequiredMixin, View):
    def post(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk)
        if survey.status != Survey.STATUS_PUBLISHED:
            return redirect("surveys-manage-edit", pk=pk)
        survey.status = Survey.STATUS_CLOSED
        survey.save(update_fields=["status", "updated_at"])
        messages.success(request, _("Survey closed."))
        return redirect("surveys-manage-edit", pk=pk)


class ManageSurveyUnpublishView(StaffRequiredMixin, View):
    def post(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk)
        if survey.status != Survey.STATUS_PUBLISHED:
            return redirect("surveys-manage-edit", pk=pk)
        survey.status = Survey.STATUS_DRAFT
        survey.save(update_fields=["status", "updated_at"])
        messages.success(request, _("Survey unpublished."))
        return redirect("surveys-manage-edit", pk=pk)


class ManageSurveyReopenView(StaffRequiredMixin, View):
    def post(self, request, pk):
        survey = get_object_or_404(Survey, pk=pk)
        if survey.status != Survey.STATUS_CLOSED:
            return redirect("surveys-manage-edit", pk=pk)
        if not survey.boundary:
            messages.error(request, _("Upload a boundary before publishing."))
            return redirect("surveys-manage-edit", pk=pk)
        survey.status = Survey.STATUS_PUBLISHED
        survey.save(update_fields=["status", "updated_at"])
        messages.success(request, _("Survey reopened."))
        return redirect("surveys-manage-edit", pk=pk)


class PublicSurveyListView(ListView):
    model = Survey
    template_name = "surveys/list.html"
    context_object_name = "surveys"

    def get_queryset(self):
        return (
            Survey.objects.filter(status=Survey.STATUS_PUBLISHED)
            .select_related("municipality")
            .order_by("-created_at")
        )


class PublicSurveyDetailView(DetailView):
    model = Survey
    template_name = "surveys/detail.html"
    context_object_name = "survey"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Survey.objects.filter(status=Survey.STATUS_PUBLISHED).prefetch_related(
            "questions__map_categories"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        survey = self.object
        questions = list(survey.questions.all())
        map_questions = [
            q for q in questions if q.question_type == SurveyQuestion.TYPE_MAP_POINTS
        ]
        context["survey_pages"] = _build_survey_pages(questions)
        context["has_boundary"] = bool(survey.boundary)
        context["has_map_questions"] = bool(map_questions)
        questions_config = {}
        for q in map_questions:
            q_config = {
                "label": q.label,
                "max_points": q.config.get("max_points", 50),
                "categories": [
                    {
                        "id": c.id,
                        "key": c.key,
                        "label": c.label,
                        "color": c.color,
                    }
                    for c in q.map_categories.all()
                ],
            }
            point_choices = q.config.get("point_choices")
            if point_choices:
                q_config["point_choices"] = point_choices
            questions_config[str(q.id)] = q_config
        context["map_config"] = {
            "slug": survey.slug,
            "boundaryUrl": reverse("surveys-boundary-geojson", kwargs={"slug": survey.slug})
            if survey.boundary
            else None,
            "questions": questions_config,
        }
        context["accepting"] = survey.is_accepting_responses
        return context


def _build_submission_payload(request, survey: Survey) -> dict:
    payload = request.POST.dict()
    for question in survey.questions.filter(
        question_type=SurveyQuestion.TYPE_MULTIPLE_CHOICE
    ):
        key = f"q_{question.id}"
        payload[key] = request.POST.getlist(key)
    return payload


class PublicSurveySubmitView(View):
    def post(self, request, slug):
        survey = get_object_or_404(Survey, slug=slug, status=Survey.STATUS_PUBLISHED)
        anonymous_key = request.session.get(f"survey_anon_{survey.slug}", "")
        try:
            response = validate_and_submit(
                survey,
                payload=_build_submission_payload(request, survey),
                user=request.user,
                anonymous_key=anonymous_key,
                client_meta={"user_agent": request.META.get("HTTP_USER_AGENT", "")[:256]},
            )
        except SubmitError as exc:
            messages.error(request, _("Please fix the errors below."))
            for key, msg in exc.errors.items():
                messages.error(request, f"{key}: {msg}")
            return redirect("surveys-detail", slug=slug)

        request.session[f"survey_anon_{survey.slug}"] = response.anonymous_key
        messages.success(request, _("Thank you — your response was submitted."))
        return redirect("surveys-detail", slug=slug)


class SurveyBoundaryGeoJSONView(View):
    def get(self, request, slug):
        survey = get_object_or_404(Survey, slug=slug, status=Survey.STATUS_PUBLISHED)
        if not survey.boundary:
            raise Http404("No boundary")
        return JsonResponse(json.loads(survey.boundary.geojson), safe=False)
