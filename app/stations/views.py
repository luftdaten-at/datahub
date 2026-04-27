import json

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from requests.exceptions import HTTPError, RequestException

from main.enums import Dimension, Order, OutputFormat, Precision
from .models import FavoriteStation
from .station_url import air_station_url_pk_by_device_ids, resolve_station_from_pk

_HISTORICAL_PRECISION_ORDER = (
    Precision.MAX,
    Precision.HOURLY,
    Precision.DAYLY,
    Precision.WEEKLY,
    Precision.MONTHLY,
    Precision.YEARYLY,
)

_HISTORICAL_PRECISION_LABELS = {
    Precision.MAX.value: _("All (max resolution)"),
    Precision.HOURLY.value: _("Hour"),
    Precision.DAYLY.value: _("Day"),
    Precision.WEEKLY.value: _("Week"),
    Precision.MONTHLY.value: _("Month"),
    Precision.YEARYLY.value: _("Year"),
}


def StationDetailView(request, pk):
    r = resolve_station_from_pk(str(pk))
    station_id = r.canonical_id
    is_favorite = False
    if request.user.is_authenticated and station_id:
        is_favorite = FavoriteStation.objects.filter(
            user=request.user, station_id=station_id
        ).exists()
    historical_precision_choices = [
        (p.value, _HISTORICAL_PRECISION_LABELS[p.value]) for p in _HISTORICAL_PRECISION_ORDER
    ]
    return render(
        request,
        "stations/detail.html",
        {
            "station_id": station_id,
            "station_detail_url_pk": r.detail_url_pk,
            "is_favorite": is_favorite,
            "is_air_station": r.is_air_station,
            "air_display_name": r.air_display_name,
            "historical_precision_choices": historical_precision_choices,
            "historical_download_default_precision": Precision.DAYLY.value,
        },
    )


class FavoriteStationToggleView(LoginRequiredMixin, View):
    """POST: add or remove this station from the user's favourites."""

    def post(self, request, pk):
        r = resolve_station_from_pk(str(pk))
        station_id = r.canonical_id[:64] if r.canonical_id else ""
        if not station_id:
            messages.error(request, _("Invalid station."))
            return redirect("stations-list")
        deleted, _delete_details = FavoriteStation.objects.filter(
            user=request.user, station_id=station_id
        ).delete()
        if deleted:
            messages.success(request, _("Removed from favourite stations."))
        else:
            FavoriteStation.objects.create(user=request.user, station_id=station_id)
            messages.success(request, _("Added to favourite stations."))
        return redirect(
            reverse("station-detail", kwargs={"pk": r.detail_url_pk})
        )

def StationListView(request):
    """
    Fetches station data for PM1, PM2.5, and PM10 dimensions.
    Returns highest and lowest values for each dimension in a dashboard-style format.
    Shows only top 5 stations for highest and lowest values, without pagination.
    """
    # Dimension mapping: PM1=2, PM2.5=3, PM10=5
    dimensions = {
        'pm1': Dimension.PM1_0,
        'pm25': Dimension.PM2_5,
        'pm10': Dimension.PM10_0,
    }

    error_message = None
    dimension_data = {}
    
    # Fetch data for each dimension
    for dim_key, dim_id in dimensions.items():
        url_min = f"{settings.API_URL}/station/topn?n=5&dimension={dim_id}&order={Order.MIN.value}&output_format={OutputFormat.CSV.value}"
        url_max = f"{settings.API_URL}/station/topn?n=5&dimension={dim_id}&order={Order.MAX.value}&output_format={OutputFormat.CSV.value}"
        
        try:
            resp_min = requests.get(
                url_min, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
            )
            resp_max = requests.get(
                url_max, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
            )

            resp_min.raise_for_status()
            resp_max.raise_for_status()

            # Skip header line (i == 0) and limit to 5 stations
            min_stations = [
                line.split(",") 
                for i, line in enumerate(resp_min.text.splitlines())
                if i
            ][:5]
            max_stations = [
                line.split(",") 
                for i, line in enumerate(resp_max.text.splitlines())
                if i
            ][:5]
            
            dimension_data[dim_key] = {
                'top_stations': max_stations,
                'lowest_stations': min_stations,
            }
            
        except (HTTPError, RequestException, Exception) as e:
            if error_message is None:
                error_message = "There was an error fetching station data: 404."
            print(f"Error fetching station data for {dim_key}: {e}")
            dimension_data[dim_key] = {
                'top_stations': [],
                'lowest_stations': [],
            }
    
    # Fetch active stations statistics from /statistics endpoint
    active_stations = {}
    
    try:
        url_statistics = f"{settings.API_URL}/statistics"
        response = requests.get(
            url_statistics, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        stats_data = response.json()
        
        # Parse active stations data
        if 'active_stations' in stats_data:
            active_stations = stats_data['active_stations']
        
    except (HTTPError, RequestException, KeyError, ValueError, Exception) as e:
        print(f"Error fetching statistics: {e}")
        active_stations = {}
    
    # Fetch all stations data from /station/all endpoint
    all_stations = []
    all_stations_json = '[]'
    
    # Check cache first
    cache_key = 'station_all_data'
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        all_stations = cached_data
    else:
        try:
            url_all_stations = f"{settings.API_URL}/station/all?output_format=json"
            response = requests.get(
                url_all_stations, timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT
            )
            response.raise_for_status()
            stations_data = response.json()
            
            # Parse stations data
            if isinstance(stations_data, list):
                for station in stations_data:
                    try:
                        station_id = station.get('id')
                        location = station.get('location', {})
                        
                        lat = location.get('lat') if isinstance(location, dict) else None
                        lon = location.get('lon') if isinstance(location, dict) else None
                        
                        if station_id and lat is not None and lon is not None:
                            all_stations.append({
                                'station_id': str(station_id),
                                'lat': float(lat),
                                'lon': float(lon),
                                'last_active': station.get('last_active', ''),
                            })
                    except (ValueError, TypeError, KeyError) as e:
                        print(f"Error parsing station data: {e}")
                        continue
            
            # Cache the parsed data for 1 hour
            cache.set(cache_key, all_stations, settings.LUFTDATEN_API_JSON_CACHE_TTL)
            
        except (HTTPError, RequestException, KeyError, ValueError, Exception) as e:
            print(f"Error fetching all stations: {e}")
            all_stations = []
    
    # Serialize to JSON for JavaScript
    all_stations_json = json.dumps(all_stations)

    air_lookup_ids: list[str] = [s["station_id"] for s in all_stations]
    for _dim_key, dim_data in dimension_data.items():
        for _section in ("top_stations", "lowest_stations"):
            for row in dim_data.get(_section) or ():
                if row and len(row) > 0 and row[0]:
                    air_lookup_ids.append(str(row[0]))
    air_url_pk = air_station_url_pk_by_device_ids(air_lookup_ids)

    context = {
        'dimension_data': dimension_data,
        'error': error_message,
        'active_stations': active_stations,
        'all_stations': all_stations,
        'all_stations_json': all_stations_json,
        'air_station_url_pk': air_url_pk,
    }

    return render(request, 'stations/list.html', context)