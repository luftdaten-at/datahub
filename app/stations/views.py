import requests
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.conf import settings
from main.enums import Dimension, SensorModel

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

            # Verarbeitung der Sensoren
            sensors = properties.get('sensors', [])
            for sensor in sensors:
                sensor_model_id = sensor.get('sensor_model')
                sensor_model_name = SensorModel.get_sensor_name(sensor_model_id)

                values = []
                for value in sensor.get('values', []):
                    dimension_id = value.get('dimension')
                    dimension_name = Dimension.get_name(dimension_id)
                    unit = Dimension.get_unit(dimension_id)
                    val = value.get('value')

                    values.append({
                        'dimension_id': dimension_id,
                        'dimension_name': dimension_name,
                        'unit': unit,
                        'value': val,
                    })

                station_info['sensors'].append({
                    'sensor_model_id': sensor_model_id,
                    'sensor_model_name': sensor_model_name,
                    'values': values,
                })
        else:
            raise Http404(f"Station mit ID {pk} nicht gefunden.")

    except requests.exceptions.HTTPError as err:
        raise Http404(f"Station mit ID {pk} nicht gefunden: {err}")
    except requests.exceptions.RequestException as e:
        return render(request, 'stations/error.html', {'error': str(e)})

    # Render die Daten im Template
    return render(request, 'stations/detail.html', {'station': station_info})

def StationListView(request):
    api_url = f"{settings.API_URL}/station/current?last_active=36000&output_format=csv"

   # top_stations = Station.objects.order_by('-value')[:10]  # Top 10 nach Feinstaubwerten
   # lowest_stations = Station.objects.order_by('value')[:10]  # Niedrigste 10 nach Feinstaubwerten
    top_stations = []
    lowest_stations = []
    
    return render(request, 'stations/list.html', {
        'top_stations': top_stations,
        'lowest_stations': lowest_stations,
    })