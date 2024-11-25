import requests
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.conf import settings

def StationDetailView(request, pk):
    # Beispiel API-URL, die von der Station-ID abhängt
    api_url = f"{settings.API_URL}/station/current?station_ids={pk}&last_active=3600&output_format=geojson"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Prüft, ob die Anfrage erfolgreich war
        station_data = response.json()  # Holt die Daten im JSON-Format
    except requests.exceptions.HTTPError as err:
        raise Http404(f"Station mit ID {pk} nicht gefunden: {err}")
    except requests.exceptions.RequestException as e:
        return render(request, 'stations/error.html', {'error': str(e)})

    # Render die Daten im Template
    return render(request, 'stations/detail.html', {'station': station_data})

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