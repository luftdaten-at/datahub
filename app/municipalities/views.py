import json

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, TemplateView

from context.models import Municipality
from main.enums import Dimension

from .city_registry import CITY_ALL_CACHE_KEY, load_city_registry_cities
from .luftdaten_city_admin import (
    CityAdminUpdateError,
    country_code_for_country_slug,
    update_city_admin,
)
from context.services import get_municipality_context

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

    ctx = get_municipality_context(municipality_slug)
    coords = municipality_info.get("coordinates") or [None, None]
    map_config = {
        "apiUrl": settings.API_URL,
        "centroid": [coords[1], coords[0]],
        "bbox": ctx.bbox,
        "slug": municipality_slug,
    }

    return render(
        request,
        "municipalities/detail.html",
        {
            "municipality": municipality_info,
            "municipality_slug": municipality_slug,
            "is_favorite": is_favorite,
            "land_profile": ctx.land,
            "heat_profile": ctx.heat,
            "peer_group": ctx.peer_group,
            "boundary_geojson": ctx.boundary_geojson,
            "bbox": ctx.bbox,
            "tiles_url": ctx.tiles_url,
            "heat_visible": ctx.heat_visible,
            "heat_metrics": ctx.heat_metrics,
            "heat_lst_range": ctx.heat_lst_range,
            "heat_acquisition_local": ctx.heat_acquisition_local,
            "map_config": map_config,
        },
    )


class MunicipalitiesApiOverviewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Superuser overview of all cities from api.luftdaten.at /city/all."""

    template_name = "municipalities/admin_overview.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cities, error = load_city_registry_cities()
        context["cities"] = cities
        context["city_registry_error"] = error
        context["luftdaten_admin_configured"] = bool(
            (settings.LUFTDATEN_ADMIN_API_KEY or "").strip()
        )
        return context


class MunicipalityAdminLocationUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """POST: update city lat/lon on api.luftdaten.at via /city/admin."""

    http_method_names = ["post"]

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def post(self, request):
        if not (settings.LUFTDATEN_ADMIN_API_KEY or "").strip():
            messages.error(
                request,
                _("Luftdaten admin API key is not configured on this server."),
            )
            return redirect("municipalities-admin-overview")

        slug = (request.POST.get("city_slug") or "").strip()
        if not slug:
            messages.error(request, _("Missing city identifier."))
            return redirect("municipalities-admin-overview")
        try:
            lat = float(request.POST.get("latitude", ""))
            lon = float(request.POST.get("longitude", ""))
        except ValueError:
            messages.error(request, _("Invalid latitude or longitude."))
            return redirect("municipalities-admin-overview")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            messages.error(request, _("Latitude and longitude are out of range."))
            return redirect("municipalities-admin-overview")

        cities, _reg_err = load_city_registry_cities()
        city_row = next((c for c in cities if c.get("slug") == slug), None)
        if city_row is None:
            messages.error(request, _("City not found in registry."))
            return redirect("municipalities-admin-overview")

        name = (city_row.get("name") or "").strip()
        if not name:
            messages.error(request, _("City has no name in registry."))
            return redirect("municipalities-admin-overview")

        country_slug = city_row.get("country_slug") or ""
        try:
            country_code = country_code_for_country_slug(country_slug)
        except CityAdminUpdateError as exc:
            messages.error(request, str(exc))
            return redirect("municipalities-admin-overview")

        try:
            cur_resp = requests.get(
                f"{settings.API_URL}/city/current",
                params={"city_slug": slug},
                timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT,
            )
            cur_resp.raise_for_status()
            feat = cur_resp.json()
        except (requests.exceptions.RequestException, ValueError, TypeError) as exc:
            messages.error(
                request,
                _("Could not load current city data: %(err)s") % {"err": str(exc)},
            )
            return redirect("municipalities-admin-overview")

        props = feat.get("properties") if isinstance(feat, dict) else None
        if not isinstance(props, dict):
            props = {}
        tz = (props.get("timezone") or "").strip()
        if not tz:
            messages.error(request, _("City has no timezone in API response."))
            return redirect("municipalities-admin-overview")

        try:
            update_city_admin(
                slug=slug,
                name=name,
                tz=tz,
                lat=lat,
                lon=lon,
                country_code=country_code,
            )
        except CityAdminUpdateError as exc:
            messages.error(request, str(exc))
            return redirect("municipalities-admin-overview")

        cache.delete(CITY_ALL_CACHE_KEY)
        messages.success(
            request,
            _("Updated location for %(name)s on api.luftdaten.at.")
            % {"name": name},
        )
        return redirect("municipalities-admin-overview")


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

    municipalities_payload = [
        {
            "name": m.name,
            "slug": m.slug,
            "country": {
                "name": m.country_code,
                "slug": m.country_code.lower(),
            },
            "location": {
                "latitude": m.centroid.y if m.centroid else None,
                "longitude": m.centroid.x if m.centroid else None,
            },
        }
        for m in Municipality.objects.order_by("name")
    ]

    translations = {
        "municipalities_with_most_stations": _(
            "Municipalities with most stations"
        ),
        "country": _("Country"),
        "stations": _("Stations"),
        "view_details": _("View Details"),
        "empty_local": _(
            "No municipalities in the local database yet. Staff can import them from the API."
        ),
    }

    translations_json = json.dumps(translations)

    return render(
        request,
        "municipalities/list.html",
        {
            "translations_json": translations_json,
            "municipality_detail_url_template": detail_url_template,
            "municipalities_payload": municipalities_payload,
        },
    )


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class ManageMunicipalityListView(StaffRequiredMixin, ListView):
    model = Municipality
    template_name = "municipalities/manage/list.html"
    context_object_name = "municipalities"
    paginate_by = 50

    def get_queryset(self):
        qs = Municipality.objects.order_by("name")
        match_method = self.request.GET.get("match_method")
        if match_method:
            qs = qs.filter(match_method=match_method)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["match_method_filter"] = self.request.GET.get("match_method", "")
        context["match_method_choices"] = Municipality.MATCH_CHOICES
        return context


class ManageMunicipalitySyncView(StaffRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        from context.sync import sync_municipalities_from_api

        created, updated, error = sync_municipalities_from_api()
        if error:
            messages.error(
                request,
                _("Sync failed: %(error)s") % {"error": error},
            )
        else:
            messages.success(
                request,
                _("Synced municipalities: %(created)s created, %(updated)s updated.")
                % {"created": created, "updated": updated},
            )
        return redirect("municipalities-manage-list")
