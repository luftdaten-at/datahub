import datetime
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import ValidationError
from django.http import JsonResponse

from main.util import get_or_create_station
from .models import AirQualityRecord, AirQualityDatapoint, MobilityMode, Measurement, DeviceLogs, Values, MeasurementNew
from workshops.models import Participant, Workshop
from devices.models import Device

from .serializers import AirQualityRecordSerializer, AirQualityDatapointSerializer, DeviceSerializer, WorkshopSerializer

   
class AirQualityDataAddView(APIView):
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
                device, _ = Device.objects.get_or_create(id=record.get('device'))
                participant, _ = Participant.objects.get_or_create(name=record.get('participant'))
                mode, _ = MobilityMode.objects.get_or_create(name=record.get('mode'))
                workshop = Workshop.objects.get(name=record.get('workshop'))
                time = parse_datetime(record.get('time'))
                
                # Check if a record already exists
                if AirQualityRecord.objects.filter(time=time, device=device).exists():
                    errors.append({'error': f'Record with time {time} and device {device.id} already exists'})
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


class DeviceDataAddView(APIView):
    """
    Processes a POST request with sensor data.

    """
    def post(self, request, format=None):
        serializer = AirQualityDatapointSerializer(data=request.data, many=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeviceStatusView(APIView):
    """
    Processes a POST request with a device status.
    
    """
    def post(self, request, *args, **kwargs):
        serializer = DeviceStatusSerializer(data=request.data, many=True)
        
        if serializer.is_valid():
            serializer.save()  # This will use the create method in the serializer
            return Response({'status': 'success'}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WorkshopDetailView(RetrieveAPIView):
    """
    Processes a GET request by returning the details of the requested Workshop as JSON.
    
    """
    queryset = Workshop.objects.all()
    serializer_class = WorkshopSerializer


class WorkshopAirQualityDataView(RetrieveAPIView):
    """
    Processes a GET request by returning the AirQualityRecords connected with the workshop name

    """
    queryset = AirQualityRecord.objects.all()
    serializer_class = AirQualityRecordSerializer

    def get(self, request, pk):
        records = AirQualityRecord.objects.filter(workshop__name=pk)
        serializer = AirQualityRecordSerializer(records, many=True)
        return Response(serializer.data)


class CreateStationStatusAPIView(APIView):
    def post(self, request, *args, **kwargs):
        print(request)
        station_data = request.data.get('station')
        status_list = request.data.get('status_list', [])

        if not station_data or not status_list:
            raise ValidationError("Both 'station' and 'status_list' are required.")

        # Get or create the station
        station = get_or_create_station(station_info=station_data)

        if station.api_key != station_data.get('apikey'):
            raise ValidationError("Wrong API Key")

        try:
            with transaction.atomic():
                for status_data in status_list:
                    # Manually create and save the DeviceLogs object
                    DeviceLogs.objects.create(
                        device=station,
                        timestamp=status_data['time'],
                        level=status_data.get('level', 1),  # Default level 1 if not provided
                        message=status_data.get('message', ''),  # Default empty message if not provided
                    )

            return Response({"status": "success"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateStationDataAPIView(APIView):
    def post(self, request, *args, **kwargs):
        print(request)
        # Parse the incoming JSON data
        try:
            station_data = request.data.get('station')
            sensors_data = request.data.get('sensors')

            if not station_data or not sensors_data:
                raise ValidationError("Both 'station' and 'sensors' are required.")

            # Use the get_or_create_station function to get or create the station
            station = get_or_create_station(station_data)

            # Record the time when the request was received
            time_received = datetime.datetime.now(datetime.timezone.utc)

            try:
                with transaction.atomic():
                    # Iterate through all sensors
                    for sensor_id, sensor_data in sensors_data.items():
                        # Check if the measurement already exists in the database
                        existing_measurement = MeasurementNew.objects.filter(
                            device=station,
                            time_measured=station_data['time'],
                            sensor_model=sensor_data['type']
                        ).first()

                        if existing_measurement:
                            return JsonResponse(
                                {"status": "error", "detail": "Measurement already in Database"},
                                status=422
                            )

                        # If no existing measurement, create a new one
                        measurement = MeasurementNew(
                            sensor_model=sensor_data['type'],
                            device=station,
                            time_measured=station_data['time'],
                            time_received=time_received,
                        )
                        measurement.save()

                        # Add values (dimension, value) for the measurement
                        for dimension, value in sensor_data['data'].items():
                            Values.objects.create(
                                dimension=dimension,
                                value=value,
                                measurement=measurement
                            )

                    # Update the station's last active time
                    station.last_update = station_data['time']
                    station.save()

                    return JsonResponse({"status": "success"}, status=201)

            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=400)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
