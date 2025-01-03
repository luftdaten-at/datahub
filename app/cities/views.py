import requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.conf import settings
from main.enums import Dimension, SensorModel, OutputFormat, Precision, Order

def CitiesDetailView(request, pk):
    api_url = f"{settings.API_URL}/city/current?city_slug={pk}"
    print(api_url)
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Prüft, ob die Anfrage erfolgreich war
        station_data = response.json()  # Daten im JSON-Format

        # Extract information from the JSON
        geometry = station_data.get("geometry", {})
        properties = station_data.get("properties", {})
        
        # Prepare city info
        city_info = {
            'name': properties.get('name'),
            'country': properties.get('country'),
            'timezone': properties.get('timezone'),
            'coordinates': geometry.get('coordinates'),
            'last_updated': properties.get('time'),
            'values': []
        }

        # Parse "values" and translate dimensions
        values = properties.get("values", [])
        for value in values:
            dimension_id = value.get("dimension")
            translated_dimension = Dimension.get_name(dimension_id)
            city_info['values'].append({
                'dimension': translated_dimension,
                'value': value.get("value"),
                'unit': Dimension.get_unit(dimension_id)
            })

    except requests.exceptions.HTTPError as err:
        raise Http404(f"City {pk} not found: {err}")
    
    except requests.exceptions.RequestException as e:
        return render(request, 'stations/error.html', {'error': str(e)})

    # Render die Daten im Template
    return render(request, 'cities/detail.html', {'city': city_info})

def CitiesListView(request):
    api_url = f"{settings.API_URL}/city/all"
    
    try:
        # Perform the GET request
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for unsuccessful requests
        data = response.json()  # Parse JSON response
        
        # Extract and sort the list of cities alphabetically by name
        cities = data.get("cities", [])
        cities = sorted(cities, key=lambda city: city.get("name", "").lower())  # Sort case-insensitively
    
    except requests.exceptions.HTTPError as err:
        raise Http404(f"Cities not found.")

    return render(request, "cities/list.html", {"cities": cities})