import json

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from main.enums import Dimension

from .models import FavoriteMunicipality


def cities_legacy_redirect(request, remainder=None):
    """Permanent redirect from old /cities/... URLs to /municipalities/..."""
    if not remainder:
        return HttpResponsePermanentRedirect("/municipalities/")
    remainder = remainder.strip("/")
    return HttpResponsePermanentRedirect(f"/municipalities/{remainder}/")


def municipality_detail_view(request, pk):
    municipality_slug = str(pk).strip()
    api_url = f"{settings.API_URL}/city/current"
    params = {"city_slug": municipality_slug}
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

        municipality_info = {
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
            municipality_info["values"].append(
                {
                    "dimension": translated_dimension,
                    "value": value.get("value"),
                    "value_count": value.get("value_count"),
                    "station_count": value.get("station_count"),
                    "unit": Dimension.get_unit(dimension_id),
                }
            )

    except requests.exceptions.HTTPError as err:
        raise Http404(
            f"Municipality {municipality_slug} not found: {err}"
        ) from err

    except requests.exceptions.RequestException as e:
        return render(request, "stations/error.html", {"error": str(e)})

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = FavoriteMunicipality.objects.filter(
            user=request.user, municipality_slug=municipality_slug
        ).exists()

    return render(
        request,
        "municipalities/detail.html",
        {
            "municipality": municipality_info,
            "municipality_slug": municipality_slug,
            "is_favorite": is_favorite,
        },
    )


class FavoriteMunicipalityToggleView(LoginRequiredMixin, View):
    """POST: add or remove this municipality from the user's favourites."""

    def post(self, request, pk):
        municipality_slug = str(pk).strip()[:128]
        if not municipality_slug:
            messages.error(request, _("Invalid municipality."))
            return redirect("municipalities-list")
        deleted, _delete_details = FavoriteMunicipality.objects.filter(
            user=request.user, municipality_slug=municipality_slug
        ).delete()
        if deleted:
            messages.success(
                request, _("Removed from favourite municipalities.")
            )
        else:
            FavoriteMunicipality.objects.create(
                user=request.user, municipality_slug=municipality_slug
            )
            messages.success(request, _("Added to favourite municipalities."))
        return redirect(
            reverse(
                "municipalities-detail", kwargs={"pk": municipality_slug}
            )
        )


def municipalities_list_view(request):
    api_url = f"{settings.API_URL}/city/all"
    error_message = None
    municipalities = []
    top_municipalities = []

    try:
        response = requests.get(
            api_url, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        municipalities = data.get("cities", [])
        municipalities = sorted(
            municipalities, key=lambda m: m.get("name", "").lower()
        )

    except requests.exceptions.HTTPError:
        error_message = "There was an error fetching the municipality data: 404."
    except requests.exceptions.RequestException:
        error_message = "There was an error fetching the municipality data."

    try:
        stats_url = f"{settings.API_URL}/statistics"
        stats_response = requests.get(
            stats_url, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
        )
        stats_response.raise_for_status()
        stats_data = stats_response.json()

        distribution = stats_data.get("distribution", {})
        top_municipalities = distribution.get("top_cities", [])

    except (requests.exceptions.HTTPError, requests.exceptions.RequestException):
        pass

    municipality_names = [
        m.get("name", "") for m in municipalities if m.get("name")
    ]

    municipality_names_json = json.dumps(municipality_names)
    municipalities_json = json.dumps(municipalities)
    top_municipalities_json = json.dumps(top_municipalities)

    detail_url_template = reverse(
        "municipalities-detail", kwargs={"pk": "__SLUG__"}
    )

    translations = {
        "municipalities_with_most_stations": _(
            "Municipalities with most stations"
        ),
        "country": _("Country"),
        "stations": _("Stations"),
        "view_details": _("View Details"),
    }

    translations_json = json.dumps(translations)

    return render(
        request,
        "municipalities/list.html",
        {
            "municipalities": municipalities,
            "error": error_message,
            "municipality_names_json": municipality_names_json,
            "municipalities_json": municipalities_json,
            "top_municipalities_json": top_municipalities_json,
            "translations_json": translations_json,
            "municipality_detail_url_template": detail_url_template,
        },
    )
