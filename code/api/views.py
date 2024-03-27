from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveAPIView

from .models import AirQualityRecord, MobilityMode
from workshops.models import Participant, Workshop
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
        if not isinstance(data, list):
            return Response({'error': 'Expected a list of records'}, status=status.HTTP_400_BAD_REQUEST)

        records = []
        errors = []
        for record in data:
            # Lookup or create the device and mobility mode instances based on provided identifiers
            device, _ = Device.objects.get_or_create(name=record.get('device'))
            mode, _ = MobilityMode.objects.get_or_create(name=record.get('mode'))

            try:
                workshop = Workshop.objects.get(name=record.get('workshop'))
                participant, _ = Participant.objects.get_or_create(name=record.get('participant'), workshop=workshop, device=device)
            except Workshop.DoesNotExist:
                return Response({'error': 'Workshop not found'}, status=status.HTTP_400_BAD_REQUEST)

            # Prepare air quality record data, replacing string identifiers with model instances
            air_quality_data = {
                **record,
                'device': device.name,
                'workshop': workshop.name,
                'participant': participant.name,
                'mode': mode.name,
            }

            serializer = AirQualityRecordSerializer(data=air_quality_data)
            if serializer.is_valid():
                serializer.save()
                records.append(serializer.data)
            else:
                errors.append(serializer.errors)

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(records, status=status.HTTP_201_CREATED)


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
    Processes a GET request by returning the AirQualityRecords connected with the workshop name

    """
    queryset = AirQualityRecord.objects.all()
    serializer_class = AirQualityRecordSerializer

    def get(self, request, pk):
        records = AirQualityRecord.objects.filter(workshop__name=pk)
        serializer = AirQualityRecordSerializer(records, many=True)
        return Response(serializer.data)