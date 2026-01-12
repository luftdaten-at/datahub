import logging
import requests
import json

from django.views.generic import TemplateView
from django.conf import settings
from main.settings import API_URL
from main import enums
from requests.exceptions import HTTPError, RequestException

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
        # Falls du den API_URL in der Template-Logik brauchst:
        context['API_URL'] = API_URL
        
        # Fetch active stations statistics from /statistics endpoint
        active_stations = {}
        
        try:
            url_statistics = f"{API_URL}/statistics"
            response = requests.get(url_statistics, timeout=10)
            response.raise_for_status()
            stats_data = response.json()
            
            # Parse active stations data
            if 'active_stations' in stats_data:
                active_stations = stats_data['active_stations']
                
        except (HTTPError, RequestException, KeyError, ValueError) as e:
            logger.error(f"Error fetching statistics: {e}")
            active_stations = {}
        
        context['active_stations'] = active_stations
        return context
    

class DocumentationPageView(TemplateView):
    template_name = "documentation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['host'] = self.request.get_host()
        return context