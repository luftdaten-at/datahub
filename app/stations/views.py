import requests
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from django.shortcuts import render
from django.http import Http404
from django.conf import settings
from django.core.cache import cache
from main.enums import OutputFormat, Precision, Order, SensorModel, Dimension
from requests.exceptions import HTTPError, RequestException

def StationDetailView(request, pk):
    # Beispiel API-URL, die von der Station-ID abhängt
    api_url = f"{settings.API_URL}/station/current?station_ids={pk}&last_active=3600&output_format=geojson"
    params = {
        'station_ids': pk,
        'last_active': 3600,
        'output_format': 'geojson',
    }
    try:
        response = requests.get(api_url, params=params)
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
            current_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            time_minus_48h = current_time - timedelta(hours=47)
            formatted_current_time = current_time.isoformat(timespec='minutes')
            formatted_time_minus_48h = time_minus_48h.isoformat(timespec='minutes')
            # api query
            api_sensor_data_48h = f"{settings.API_URL}/station/historical"
            params = {
                'station_ids': pk,
                'output_format': OutputFormat.JSON.value,
                'precision': Precision.HOURLY.value,
                'start': formatted_time_minus_48h,
                'end': formatted_current_time,
            }
            response = requests.get(api_sensor_data_48h, params=params)
            response.raise_for_status()
            data_48h = response.json()
            dim_hour_val = defaultdict(lambda: [0 for _ in range(48)])
            for data_hour in data_48h:
                hour = datetime.fromisoformat(data_hour["time_measured"])
                hour = hour.replace(tzinfo=timezone.utc)

                for dim_val in data_hour["values"]:
                    dim = dim_val["dimension"]
                    val = dim_val["value"]
                    # Calculate hour index and ensure it's within bounds [0, 47]
                    hour_index = int((hour - time_minus_48h).total_seconds() // 3600)
                    if 0 <= hour_index < 48:
                        dim_hour_val[str(dim)][hour_index] = val
                    else:
                        # Log out-of-range data for debugging
                        print(f"Warning: Hour index {hour_index} out of range [0, 47] for station {pk}, hour: {hour}, time_minus_48h: {time_minus_48h}")

            dims_for_display = [2, 3, 5, 6, 7]
            for dim in dims_for_display:
                dim = str(dim)
                if dim not in dim_hour_val:
                    dim_hour_val[dim] = 'false' 
            station_info["data_48h"] = dim_hour_val

            # build sensor info
            api_url = f"{settings.API_URL}/station/info"
            params = {
                'station_id': pk,
            }
            response = requests.get(api_url, params=params)
            response.raise_for_status()  # Prüft, ob die Anfrage erfolgreich war
            info = response.json()  # Daten im JSON-Format
            sensors = [SensorModel.get_sensor_name(v['type']) for _, v in info['sensors'].items()]
        else:
            raise Http404(f"Station mit ID {pk} nicht gefunden.")

    except requests.exceptions.HTTPError as err:
        raise Http404(f"Station mit ID {pk} nicht gefunden: {err}")
    except requests.exceptions.RequestException as e:
        return render(request, 'stations/error.html', {'error': str(e)})

    # Render die Daten im Template
    return render(request, 'stations/detail.html', {'station': station_info, 'sensors' : sensors})

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
            resp_min = requests.get(url_min)
            resp_max = requests.get(url_max)

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
            
        except (HTTPError, RequestException) as e:
            if error_message is None:
                error_message = "There was an error fetching station data: 404."
            print(f"Error fetching station data for {dim_key}: {e}")
            dimension_data[dim_key] = {
                'top_stations': [],
                'lowest_stations': [],
            }
    
    # Fetch all stations with coordinates from /station/all (with caching)
    cache_key = 'station_all_data'
    cache_timeout = 3600  # Cache for 1 hour (3600 seconds)
    
    all_stations = cache.get(cache_key)
    
    if all_stations is None:
        # Cache miss - fetch from API
        all_stations = []
        try:
            url_all = f"{settings.API_URL}/station/all?output_format={OutputFormat.JSON.value}"
            resp_all = requests.get(url_all, timeout=30)
            resp_all.raise_for_status()
            
            # Parse JSON response
            # Expected format: [{"id": "354SC", "location": {"lat": 47.095, "lon": 13.721}, ...}, ...]
            stations_data = resp_all.json()
            
            if isinstance(stations_data, list):
                for station in stations_data:
                    try:
                        station_id = station.get('id')
                        location = station.get('location', {})
                        
                        if isinstance(location, dict):
                            lat = location.get('lat')
                            lon = location.get('lon')
                        else:
                            lat = None
                            lon = None
                        
                        if station_id and lat is not None and lon is not None:
                            all_stations.append({
                                'station_id': str(station_id),
                                'lat': float(lat),
                                'lon': float(lon),
                                'last_active': station.get('last_active', ''),
                            })
                        else:
                            print(f"Station missing required fields: id={station_id}, lat={lat}, lon={lon}")
                    except (ValueError, TypeError, KeyError) as e:
                        print(f"Error parsing station data: {e}, station: {station}")
                        continue
            else:
                print(f"Unexpected JSON structure. Expected list, got: {type(stations_data)}")
            
            # Store in cache
            cache.set(cache_key, all_stations, cache_timeout)
            print(f"Fetched {len(all_stations)} stations from API")
        except (HTTPError, RequestException) as e:
            print(f"Error fetching all stations data: {e}")
            all_stations = []
        except (ValueError, KeyError) as e:
            print(f"Error parsing JSON response: {e}")
            all_stations = []
    
    # Fetch active stations statistics from /statistics endpoint
    active_stations = {}
    
    try:
        url_statistics = f"{settings.API_URL}/statistics"
        response = requests.get(url_statistics, timeout=10)
        response.raise_for_status()
        stats_data = response.json()
        
        # Parse active stations data
        if 'active_stations' in stats_data:
            active_stations = stats_data['active_stations']
        
    except (HTTPError, RequestException, KeyError, ValueError) as e:
        print(f"Error fetching statistics: {e}")
        active_stations = {}
    
    # Serialize all_stations to JSON for JavaScript
    all_stations_json = json.dumps(all_stations)

    context = {
        'dimension_data': dimension_data,
        'error': error_message,
        'all_stations': all_stations,
        'all_stations_json': all_stations_json,
        'active_stations': active_stations,
    }

    return render(request, 'stations/list.html', context)