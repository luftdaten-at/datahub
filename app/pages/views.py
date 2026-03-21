import logging

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from requests.exceptions import RequestException

from main.settings import API_URL

logger = logging.getLogger(__name__)


class HelpPageView(TemplateView):
    template_name = "help.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['host'] = self.request.get_host()
        return context


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
        context['host'] = self.request.get_host()
        return context


class LuftdatenStatisticsProxyView(View):
    """Same-origin JSON proxy for api.luftdaten.at /statistics (avoids browser CORS / redirect limits)."""

    cache_key = "luftdaten_statistics_proxy:payload"

    def get(self, request, *args, **kwargs):
        cache_key = f"{self.cache_key}:{API_URL}"
        cached = cache.get(cache_key)
        if cached is not None:
            return JsonResponse(cached)

        url = f"{API_URL}/statistics"
        try:
            response = requests.get(
                url, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            cache.set(cache_key, data, settings.LUFTDATEN_API_JSON_CACHE_TTL)
            return JsonResponse(data)
        except (RequestException, ValueError, TypeError) as e:
            logger.warning("Luftdaten statistics proxy failed: %s", e)
            return JsonResponse({"active_stations": {}})
