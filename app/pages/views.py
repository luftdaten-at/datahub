import json

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from main.settings import API_URL

from .forms import FAQEntryStaffForm
from .geosphere_chem import (
    CHEM_ALLOWED_PARAMETERS,
    fetch_chem_grid_geojson,
    fetch_chem_metadata_cached,
    fetch_chem_timestamps_cached,
    select_chem_forecast_hour_iso,
)
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
        context["geosphere_chem_metadata_url"] = reverse(
            "geosphere-chem-forecast-metadata"
        )
        context["geosphere_chem_grid_url"] = reverse(
            "geosphere-chem-forecast-grid"
        )
        return context


class GeosphereChemForecastMetadataProxyView(View):
    """Proxies GeoSphere chem-v2-1h-3km grid forecast metadata (cached)."""

    http_method_names = ["get"]

    def get(self, request):
        data = fetch_chem_metadata_cached()
        if data is None:
            return JsonResponse({"error": "upstream_unavailable"}, status=502)
        return JsonResponse(data)


class GeosphereChemForecastGridProxyView(View):
    """Proxies chem forecast GeoJSON for one parameter, Austria bbox, nearest forecast hour."""

    http_method_names = ["get"]

    def get(self, request):
        param = (request.GET.get("parameter") or "pm25surf").strip()
        if param not in CHEM_ALLOWED_PARAMETERS:
            return JsonResponse({"detail": "invalid parameter"}, status=400)

        bbox = (request.GET.get("bbox") or "").strip()
        if not bbox:
            bbox = settings.GEOSPHERE_CHEM_DEFAULT_BBOX

        try:
            forecast_offset = int(request.GET.get("forecast_offset", "0"))
        except ValueError:
            forecast_offset = 0

        timestamps = fetch_chem_timestamps_cached(forecast_offset)
        hour_iso = select_chem_forecast_hour_iso(timestamps)
        if hour_iso is None:
            return self._empty_geojson(502)

        cache_key = "geosphere_chem_grid:{}:{}:{}:{}".format(
            param, hour_iso, bbox, forecast_offset
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return self._json_response(cached)

        payload = fetch_chem_grid_geojson(param, bbox, hour_iso, forecast_offset)
        if payload is None:
            return self._empty_geojson(502)

        try:
            body_str = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError):
            return self._empty_geojson(502)

        cache.set(cache_key, payload, settings.GEOSPHERE_API_CACHE_TTL)
        return HttpResponse(
            body_str.encode("utf-8"),
            content_type="application/geo+json; charset=utf-8",
        )

    def _empty_geojson(self, status):
        return HttpResponse(
            '{"type":"FeatureCollection","features":[]}',
            status=status,
            content_type="application/geo+json; charset=utf-8",
        )

    def _json_response(self, payload):
        body_str = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        return HttpResponse(
            body_str.encode("utf-8"),
            content_type="application/geo+json; charset=utf-8",
        )


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
