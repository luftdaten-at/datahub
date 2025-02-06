import logging
import requests

from django.views.generic import TemplateView
from django.conf import settings

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

        # # 1. Fetch the city data (JSON)
        # api_url_cities = f"{settings.API_URL}/city/all"
        # cities = []
        # cities_number = 0  # Default if fetching fails

        # try:
        #     response = requests.get(api_url_cities)
        #     response.raise_for_status()
        #     data = response.json()
        #     cities = data.get("cities", [])
        #     cities_number = len(cities)
        # except requests.exceptions.HTTPError as err_http:
        #     logger.error("HTTPError while fetching city data from %s: %s", api_url_cities, err_http)
        #     error_message = "There was an error fetching the city data: 404."
        #     context['error_message'] = error_message
        # except requests.exceptions.RequestException as err_req:
        #     logger.error("RequestException while fetching city data from %s: %s", api_url_cities, err_req)
        #     error_message = "There was an error fetching the city data."
        #     context['error_message'] = error_message

        # context['cities_number'] = cities_number

        # # 2. Fetch the station data (CSV)
        # api_url_stations = f"{settings.API_URL}/station/current"
        # stations = []
        # stations_number = 0 # Default if fetching fails

        # try:
        #     response = requests.get(api_url_stations)
        #     response.raise_for_status()
        #     data = response.json()
        #     stations = data.get("device", [])
        #     stations_number = len(stations)
        # except requests.exceptions.HTTPError as err_http:
        #     logger.error("HTTPError while fetching station data from %s: %s", api_url_stations, err_http)
        #     error_message = "There was an error fetching the station data: 404."
        #     context['error_message'] = error_message
        # except requests.exceptions.RequestException as err_req:
        #     logger.error("RequestException while fetching station data from %s: %s", api_url_stations, err_req)
        #     error_message = "There was an error fetching the station data."
        #     context['error_message'] = error_message

        # context['stations_number'] = stations_number

        return context
    

class DocumentationPageView(TemplateView):
    template_name = "documentation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['host'] = self.request.get_host()
        return context