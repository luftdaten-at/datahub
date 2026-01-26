import requests
import json
from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from main.enums import OutputFormat, Precision, Order, SensorModel, Dimension
from requests.exceptions import HTTPError, RequestException

def StationDetailView(request, pk):
    # Only pass the station ID to the template - API calls are now in JavaScript
    return render(request, 'stations/detail.html', {'station_id': pk})

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
        response = requests.get(url_statistics, timeout=10)
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
            response = requests.get(url_all_stations, timeout=10)
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
            cache.set(cache_key, all_stations, 3600)
            
        except (HTTPError, RequestException, KeyError, ValueError, Exception) as e:
            print(f"Error fetching all stations: {e}")
            all_stations = []
    
    # Serialize to JSON for JavaScript
    all_stations_json = json.dumps(all_stations)
    
    context = {
        'dimension_data': dimension_data,
        'error': error_message,
        'active_stations': active_stations,
        'all_stations': all_stations,
        'all_stations_json': all_stations_json,
    }

    return render(request, 'stations/list.html', context)