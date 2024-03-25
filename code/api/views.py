from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveAPIView

from .models import AirQualityRecord
from workshops.models import Workshop
from devices.models import Device

from .serializers import AirQualityRecordSerializer, DeviceSerializer, WorkshopSerializer


class AirQualityDataAdd(APIView):
    """
    Processes a POST request containing JSON data about air quality records. Each record includes information
    about air quality metrics, the device reporting the data, the workshop associated with the data,
    and the location of the measurement. This view attempts to parse the JSON data, create or retrieve
    related instances (Device, Workshop), and save each air quality record to the database.
    """
    serializer_class = AirQualityRecordSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            # Lookup or create the device and workshop instances based on provided identifiers
            device, _ = Device.objects.get_or_create(name=data.get('device'))
            workshop, _ = Workshop.objects.get(id=data.get('workshop'))

            # Prepare air quality record data, replacing string identifiers with model instances
            air_quality_data = {
                **data,
                'device': device.name,
                'workshop': workshop.id,
                'lat': data.get('lat'),
                'lon': data.get('lon'),
                'location_precision': data.get('location_precision')
            }

            serializer = AirQualityRecordSerializer(data=air_quality_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DeviceDetailView(RetrieveAPIView):
    """
    Processes a GET request by returning the details of the requested Device as JSON.
    
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer


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
    def get(self, request, pk):
        records = AirQualityRecord.objects.filter(workshop__id=pk)
        serializer = AirQualityRecordSerializer(records, many=True)
        return Response(serializer.data)