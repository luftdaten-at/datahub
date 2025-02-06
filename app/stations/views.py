import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from django.shortcuts import render
from django.http import Http404
from django.conf import settings
from main.enums import OutputFormat, Precision, Order
from requests.exceptions import HTTPError, RequestException
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def StationDetailView(request, pk):
    # Beispiel API-URL, die von der Station-ID abhängt
    api_url = f"{settings.API_URL}/station/current?station_ids={pk}&last_active=3600&output_format=geojson"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Prüft, ob die Anfrage erfolgreich war
        station_data = response.json()  # Daten im JSON-Format

        # Überprüfen, ob "features" vorhanden und nicht leer sind
        if station_data.get('features'):
            feature = station_data['features'][0]  # Da nur eine Station erwartet wird
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            
            # Extrahieren der relevanten Informationen
            station_info = {
                'id': properties.get('device'),
                'time': properties.get('time'),
                'height': properties.get('height'),
                'coordinates': geometry.get('coordinates'),
                'sensors': [],
            }
            current_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
            time_minus_48h = current_time - timedelta(hours=47)
            formatted_current_time = current_time.isoformat(timespec='minutes')
            formatted_time_minus_48h = time_minus_48h.isoformat(timespec='minutes')
            # api query
            api_sensor_data_48h = f"{settings.API_URL}/station/historical?station_ids={pk}&output_format={OutputFormat.JSON.value}&precision={Precision.HOURLY.value}&start={formatted_time_minus_48h}&end={formatted_current_time}"
            print(api_sensor_data_48h)
            response = requests.get(api_sensor_data_48h)
            response.raise_for_status()
            data_48h = response.json()
            dim_hour_val = defaultdict(lambda: [0 for _ in range(48)])
            for data_hour in data_48h:
                hour = datetime.fromisoformat(data_hour["time_measured"])
                for dim_val in data_hour["values"]:
                    dim = dim_val["dimension"]
                    val = dim_val["value"]
                    dim_hour_val[str(dim)][int((hour - time_minus_48h).total_seconds() // 3600)] = val

            station_info["data_48h"] = dim_hour_val
        else:
            raise Http404(f"Station mit ID {pk} nicht gefunden.")

    except requests.exceptions.HTTPError as err:
        raise Http404(f"Station mit ID {pk} nicht gefunden: {err}")
    except requests.exceptions.RequestException as e:
        return render(request, 'stations/error.html', {'error': str(e)})

    # Render die Daten im Template
    return render(request, 'stations/detail.html', {'station': station_info})

def StationListView(request):
    """
    Fetches two lists: stations with the highest PM2.5 values and 
    stations with the lowest PM2.5 values.
    """
    url_min = f"{settings.API_URL}/station/topn?n=100&dimension=3&order={Order.MIN.value}&output_format={OutputFormat.CSV.value}"    
    url_max = f"{settings.API_URL}/station/topn?n=100&dimension=3&order={Order.MAX.value}&output_format={OutputFormat.CSV.value}"    

    error_message = None
    try:
        resp_min = requests.get(url_min)
        resp_max = requests.get(url_max)

        # Raise HTTPError for bad responses
        resp_min.raise_for_status()
        resp_max.raise_for_status()

        # Skip header line (i == 0)
        min_stations = [
            line.split(",") 
            for i, line in enumerate(resp_min.text.splitlines())
            if i
        ]
        max_stations = [
            line.split(",") 
            for i, line in enumerate(resp_max.text.splitlines())
            if i
        ]

    except (HTTPError, RequestException) as e:
        # Instead of raising a 404, store an error message in the context.
        error_message = "There was an error fetching station data: 404."
        # Optionally, you can log the error:
        print(f"Error fetching station data: {e}")
        min_stations = []
        max_stations = []

    # Paginate each list separately
    paginator_top = Paginator(max_stations, 10)
    paginator_low = Paginator(min_stations, 10)

    page_top = request.GET.get('page_top')
    page_low = request.GET.get('page_low')

    try:
        top_stations_page = paginator_top.page(page_top)
    except PageNotAnInteger:
        top_stations_page = paginator_top.page(1)
    except EmptyPage:
        top_stations_page = paginator_top.page(paginator_top.num_pages)

    try:
        lowest_stations_page = paginator_low.page(page_low)
    except PageNotAnInteger:
        lowest_stations_page = paginator_low.page(1)
    except EmptyPage:
        lowest_stations_page = paginator_low.page(paginator_low.num_pages)

    context = {
        'top_stations': top_stations_page,
        'lowest_stations': lowest_stations_page,
        'paginator_top': paginator_top,
        'paginator_low': paginator_low,
        'page_top': top_stations_page,
        'page_low': lowest_stations_page,
        'error': error_message,
    }

    return render(request, 'stations/list.html', context)