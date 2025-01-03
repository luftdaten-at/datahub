import requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.conf import settings
from main.enums import Dimension, SensorModel, OutputFormat, Precision, Order

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
            current_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
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
    max_station: List[Tuple[device,time_measured,dimension,value]]
    min_stations: List[Tuple[device,time_measured,dimension,value]]
    """

    url_min = f"{settings.API_URL}/station/topn?n=10&dimension=3&order={Order.MIN.value}&output_format={OutputFormat.CSV.value}"    
    url_max = f"{settings.API_URL}/station/topn?n=10&dimension=3&order={Order.MAX.value}&output_format={OutputFormat.CSV.value}"    
    
    resp_min = requests.get(url_min)
    resp_max = requests.get(url_max)

    # TODO: try catch
    resp_min.raise_for_status()
    resp_max.raise_for_status()

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

    return render(request, 'stations/list.html', {
        'top_stations': max_stations,
        'lowest_stations': min_stations,
    })
