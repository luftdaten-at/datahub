import requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.conf import settings
from main.enums import Dimension, SensorModel, OutputFormat, Precision, Order

def CitiesDetailView(request, pk):
    api_url = f"{settings.API_URL}/city/current"
    params = {
        "city_slug": {pk},
    }
    try:
        response = requests.get(api_url, params=params)
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
            'station_count': properties.get('station_count'),
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
                'value_count': value.get('value_count'),
                'station_count': value.get('station_count'),
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
    error_message = None
    cities = []

    try:
        # Perform the GET request
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for unsuccessful requests
        data = response.json()  # Parse JSON response

        # Extract and sort the list of cities alphabetically by name
        cities = data.get("cities", [])
        cities = sorted(cities, key=lambda city: city.get("name", "").lower())  # Sort case-insensitively

    except requests.exceptions.HTTPError as err:
        # Instead of raising a 404, store an error message to be shown in the template.
        error_message = "There was an error fetching the city data: 404."
    except requests.exceptions.RequestException as err:
        # Catch any other request exceptions that might occur.
        error_message = "There was an error fetching the city data."

    return render(request, "cities/list.html", {"cities": cities, "error": error_message})