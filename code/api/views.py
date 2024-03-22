from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveAPIView

from .models import Location, AirQualityRecord
from workshops.models import Workshop
from devices.models import Device

from .serializers import AirQualityRecordSerializer, WorkshopSerializer
import json

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action


@extend_schema(tags=['Air Quality Records'])
class AirQualityDataAdd(APIView):
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
    """
    def post(self, request):
        data = request.data  # DRF parses the request body
        try:
            records = []
            for record in data:
                location_data = record.pop('location', {})
                location, _ = Location.objects.get_or_create(**location_data)

                device, _ = Device.objects.get_or_create(name=record.pop('device', {}))
                workshop, _ = Workshop.objects.get_or_create(id=record.pop('workshop'))

                air_quality_record = AirQualityRecord.objects.create(**record, location=location, device=device, workshop=workshop)
                records.append(air_quality_record)

            serializer = AirQualityRecordSerializer(records, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WorkshopDetailView(RetrieveAPIView):
    """
    Processes a GET request by returning the details of the requested Workshop as JSON.
    
    """
    queryset = Workshop.objects.all()
    serializer_class = WorkshopSerializer


class WorkshopAirQualityData(RetrieveAPIView):
    """
    Processes a GET request by returning the AirQualityRecords connected with the workshop ID

    """
    def get(self, request, workshop_id):
        records = AirQualityRecord.objects.filter(workshop__id=workshop_id)
        serializer = AirQualityRecordSerializer(records, many=True)
        return Response(serializer.data)