import json

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from main.enums import Dimension
from .models import FavoriteCity


def CitiesDetailView(request, pk):
    city_slug = str(pk).strip()
    api_url = f"{settings.API_URL}/city/current"
    params = {"city_slug": city_slug}
    try:
        response = requests.get(
            api_url,
            params=params,
            timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        station_data = response.json()

        geometry = station_data.get("geometry", {})
        properties = station_data.get("properties", {})

        city_info = {
            "name": properties.get("name"),
            "country": properties.get("country"),
            "timezone": properties.get("timezone"),
            "coordinates": geometry.get("coordinates"),
            "last_updated": properties.get("time"),
            "station_count": properties.get("station_count"),
            "values": [],
        }

        values = properties.get("values", [])
        for value in values:
            dimension_id = value.get("dimension")
            translated_dimension = Dimension.get_name(dimension_id)
            city_info["values"].append(
                {
                    "dimension": translated_dimension,
                    "value": value.get("value"),
                    "value_count": value.get("value_count"),
                    "station_count": value.get("station_count"),
                    "unit": Dimension.get_unit(dimension_id),
                }
            )

    except requests.exceptions.HTTPError as err:
        raise Http404(f"City {city_slug} not found: {err}") from err

    except requests.exceptions.RequestException as e:
        return render(request, "stations/error.html", {"error": str(e)})

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = FavoriteCity.objects.filter(
            user=request.user, city_slug=city_slug
        ).exists()

    return render(
        request,
        "cities/detail.html",
        {
            "city": city_info,
            "city_slug": city_slug,
            "is_favorite": is_favorite,
        },
    )


class FavoriteCityToggleView(LoginRequiredMixin, View):
    """POST: add or remove this city from the user's favourites."""

    def post(self, request, pk):
        city_slug = str(pk).strip()[:128]
        if not city_slug:
            messages.error(request, _("Invalid city."))
            return redirect("cities-list")
        deleted, _delete_details = FavoriteCity.objects.filter(
            user=request.user, city_slug=city_slug
        ).delete()
        if deleted:
            messages.success(request, _("Removed from favourite cities."))
        else:
            FavoriteCity.objects.create(user=request.user, city_slug=city_slug)
            messages.success(request, _("Added to favourite cities."))
        return redirect(reverse("cities-detail", kwargs={"pk": city_slug}))


def CitiesListView(request):
    api_url = f"{settings.API_URL}/city/all"
    error_message = None
    cities = []
    top_cities = []

    try:
        response = requests.get(
            api_url, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        cities = data.get("cities", [])
        cities = sorted(cities, key=lambda city: city.get("name", "").lower())

    except requests.exceptions.HTTPError:
        error_message = "There was an error fetching the city data: 404."
    except requests.exceptions.RequestException:
        error_message = "There was an error fetching the city data."

    try:
        stats_url = f"{settings.API_URL}/statistics"
        stats_response = requests.get(
            stats_url, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
        )
        stats_response.raise_for_status()
        stats_data = stats_response.json()

        distribution = stats_data.get("distribution", {})
        top_cities = distribution.get("top_cities", [])

    except (requests.exceptions.HTTPError, requests.exceptions.RequestException):
        pass

    city_names = [city.get("name", "") for city in cities if city.get("name")]

    city_names_json = json.dumps(city_names)
    cities_json = json.dumps(cities)
    top_cities_json = json.dumps(top_cities)

    translations = {
        "cities_with_most_stations": _("Cities with Most Stations"),
        "country": _("Country"),
        "stations": _("Stations"),
        "view_details": _("View Details"),
    }

    translations_json = json.dumps(translations)

    return render(
        request,
        "cities/list.html",
        {
            "cities": cities,
            "error": error_message,
            "city_names_json": city_names_json,
            "cities_json": cities_json,
            "top_cities_json": top_cities_json,
            "translations_json": translations_json,
        },
    )
