import json

from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from main.settings import API_URL

from .forms import FAQEntryStaffForm
from .models import FAQEntry


def _faq_entry_json(entry):
    return {
        "id": entry.pk,
        "question": entry.question,
        "answer": entry.answer,
        "is_published": entry.is_published,
        "sort_order": entry.sort_order,
    }


class StaffFAQAPIMixin:
    """JSON API for FAQ editing; staff only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


class HelpPageView(TemplateView):
    template_name = "help.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["host"] = self.request.get_host()
        user = self.request.user
        can_edit = user.is_authenticated and user.is_staff
        context["can_edit_faq"] = can_edit
        if can_edit:
            entries = list(
                FAQEntry.objects.all().order_by("sort_order", "pk")
            )
            context["faq_entries"] = entries
            context["faq_entries_data"] = [_faq_entry_json(e) for e in entries]
            context["faq_api_detail_placeholder_pk"] = 987654321
        else:
            context["faq_entries"] = FAQEntry.objects.filter(
                is_published=True
            ).order_by("sort_order", "pk")
        return context


class FAQReorderView(StaffFAQAPIMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode() or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        order = body.get("order")
        if not isinstance(order, list):
            return JsonResponse({"error": "order must be a list"}, status=400)
        try:
            order_ids = [int(x) for x in order]
        except (TypeError, ValueError):
            return JsonResponse({"error": "order must contain integers"}, status=400)

        all_ids = set(FAQEntry.objects.values_list("pk", flat=True))
        if set(order_ids) != all_ids or len(order_ids) != len(all_ids):
            return JsonResponse({"error": "order must list each FAQ id exactly once"}, status=400)

        with transaction.atomic():
            for index, pk in enumerate(order_ids):
                FAQEntry.objects.filter(pk=pk).update(sort_order=index)

        return JsonResponse({"ok": True})


class FAQCreateView(StaffFAQAPIMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode() or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({"error": "Body must be a JSON object"}, status=400)

        max_order = FAQEntry.objects.aggregate(m=Max("sort_order"))["m"]
        next_order = (max_order + 1) if max_order is not None else 0

        form = FAQEntryStaffForm(data)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)

        entry = form.save(commit=False)
        entry.sort_order = next_order
        entry.updated_by = request.user
        entry.save()

        return JsonResponse({"ok": True, "entry": _faq_entry_json(entry)}, status=201)


class FAQEntryDetailView(StaffFAQAPIMixin, View):
    def patch(self, request, pk, *args, **kwargs):
        entry = get_object_or_404(FAQEntry, pk=pk)
        try:
            data = json.loads(request.body.decode() or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({"error": "Body must be a JSON object"}, status=400)

        payload = {
            "question": entry.question,
            "answer": entry.answer,
            "is_published": entry.is_published,
        }
        for key in ("question", "answer", "is_published"):
            if key in data:
                payload[key] = data[key]

        form = FAQEntryStaffForm(payload, instance=entry)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)

        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()

        return JsonResponse({"ok": True, "entry": _faq_entry_json(obj)})

    def delete(self, request, pk, *args, **kwargs):
        entry = get_object_or_404(FAQEntry, pk=pk)
        entry.delete()
        return JsonResponse({"ok": True})


class HomePageView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['host'] = self.request.get_host()
        context['API_URL'] = API_URL
        return context


class DocumentationPageView(TemplateView):
    template_name = "documentation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["host"] = self.request.get_host()
        context["documentation_sections"] = [
            {
                "title": _("App"),
                "description": _(
                    "Step-by-step guides for the Luftdaten.at mobile app, "
                    "including exporting measurements as JSON or CSV."
                ),
                "url": "https://luftdaten.at/anleitungen/anleitung-app/",
            },
            {
                "title": _("Datahub"),
                "description": _(
                    "Instructions for using the Datahub on the web: explore "
                    "data, devices, and citizen science features."
                ),
                "url": "https://luftdaten.at/anleitungen/anleitung-datahub/",
            },
            {
                "title": _("Air Station"),
                "description": _(
                    "Assembly, configuration, and WiFi setup for the "
                    "Air Station 3 measuring device."
                ),
                "url": "https://luftdaten.at/anleitungen/anleitung-air-station-3-wifi/",
            },
        ]
        return context
