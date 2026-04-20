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
            "translations_json": translations_json,
            "municipality_detail_url_template": detail_url_template,
        },
    )
