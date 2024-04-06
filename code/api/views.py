from django.db import IntegrityError
from django.utils.dateparse import parse_datetime

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
            try:
                device, _ = Device.objects.get_or_create(name=record.get('device'))
                participant, _ = Participant.objects.get_or_create(name=record.get('participant'))
                mode, _ = MobilityMode.objects.get_or_create(name=record.get('mode'))
                workshop = Workshop.objects.get(name=record.get('workshop'))
                time = parse_datetime(record.get('time'))
                
                # Check if a record already exists
                if AirQualityRecord.objects.filter(time=time, device=device).exists():
                    errors.append({'error': f'Record with time {time} and device {device.name} already exists'})
                    continue  # Skip this record and continue with the next one
                
                 # Check if the time of the record is within the workshop's timeframe
                if not (workshop.start_date <= time <= workshop.end_date):
                    errors.append({'error': f'The time {time} of the record is not within the start and end date of the workshop.'})
                    continue # Skip this record and continue with the next one

                air_quality_data = {
                    **record,
                    'device': device,
                    'workshop': record.get('workshop'),
                    'participant': participant,
                    'mode': mode,
                }

                serializer = AirQualityRecordSerializer(data=air_quality_data)
                if serializer.is_valid():
                    serializer.save()
                    records.append(serializer.data)
                else:
                    errors.append(serializer.errors)
            except Workshop.DoesNotExist:
                errors.append({'error': 'Workshop not found'})
            except IntegrityError as e:
                errors.append({'error': str(e)})

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