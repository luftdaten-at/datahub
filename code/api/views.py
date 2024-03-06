from django.http import JsonResponse, HttpResponseBadRequest, Http404
from .models import AirQualityRecord, Location
from workshops.models import Workshop
from devices.models import Device
import json
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def air_quality_data_add(request):
    """
    Processes a POST request containing JSON data about air quality records. Each record includes information
    about air quality metrics, the device reporting the data, the workshop associated with the data,
    and the location of the measurement. This view attempts to parse the JSON data, create or retrieve
    related instances (Device, Workshop, Location), and save each air quality record to the database.

    Args:
        request (HttpRequest): The request object used to access the POST data. It is expected to contain
                               a JSON body with a list of air quality record objects.

    Returns:
        JsonResponse: An HTTP response object that indicates the outcome of the operation. It returns
                      a status code of 201 (Created) if all records are processed successfully, or
                      400 (Bad Request) with an error message if an exception occurs.

    Example POST data format:
        [{
            "time": "2019-01-01T00:00:00+00:00",
            "pm1": 10,
            "pm25": 20,
            "pm10": 30,
            "temperature": 20,
            "humidity": 50,
            "voc": 100,
            "nox": 200,
            "device": "B040",
            "workshop": "i7847g",
            "location": {
                "lat": 51.509865,
                "lon": -0.118092,
                "precision": 10
            }
        }]

    Note:
        This view is CSRF exempt, making it more accessible from external clients without requiring a CSRF token.
        Ensure that proper authentication and permissions checks are implemented in production environments
        to secure the endpoint.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for record in data:
                location_data = record.pop('location', {})
                location, _ = Location.objects.get_or_create(**location_data)

                device, _ = Device.objects.get_or_create(name=record.pop('device'))
                workshop, _ = Workshop.objects.get_or_create(unique_id=record.pop('workshop'))

                AirQualityRecord.objects.create(**record, location=location, device=device, workshop=workshop)
            return JsonResponse({"status": "success"}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return HttpResponseBadRequest("Only POST requests are allowed")

def workshop_detail(request, pk):
    """
    Processes a GET request by returning the details of the requested Workshop as JSON.
    
    """
    try:
        workshop = Workshop.objects.get(pk=pk)
    except Workshop.DoesNotExist:
        raise Http404("Workshop not found")
    
    # Prepare the data to be JSON-serializable
    data = {
        "id": workshop.id,
        "title": workshop.title,
        "description": workshop.description,
        "start_date": workshop.start_date.strftime('%Y-%m-%d %H:%M:%S'),  # Format the date as a string
        "end_date": workshop.end_date.strftime('%Y-%m-%d %H:%M:%S'),  # Format the date as a string
    }
    return JsonResponse(data)