from datetime import datetime, timezone
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime

from devices.models import DeviceLogs, Measurement, Values
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import ValidationError
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema

from main.util import get_or_create_station
from .models import AirQualityRecord, MobilityMode
from workshops.models import Participant, Workshop
from devices.models import Device
from main import enums

from .serializers import AirQualityRecordSerializer, AirQualityRecordWorkshopSerializer, DeviceSerializer, WorkshopSerializer, StationDataSerializer, StationStatusSerializer


@extend_schema(tags=['workshops']) 
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
                mac = record.get('device').upper()
                rmac = ''.join(reversed([mac[i:i+2] for i in range(0, len(mac), 2)]))

                device_id = f'{rmac}AAA'

                device, _ = Device.objects.get_or_create(id=device_id)
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


@extend_schema(tags=['workshops'])
class WorkshopDetailView(RetrieveAPIView):
    """
    Processes a GET request by returning the details of the requested Workshop as JSON.
    
    """
    queryset = Workshop.objects.all()
    serializer_class = WorkshopSerializer


@extend_schema(tags=['workshops'])
class WorkshopAirQualityDataView(RetrieveAPIView):
    """
    Processes a GET request by returning the AirQualityRecords connected with the workshop name

    """
    queryset = AirQualityRecord.objects.all()
    serializer_class = AirQualityRecordWorkshopSerializer

    def get(self, request, pk):
        '''
        records = AirQualityRecord.objects.filter(workshop__name=pk)
        serializer = AirQualityRecordWorkshopSerializer(records, many=True)

        return Response(serializer.data)
        '''

        aqr_reverse = {v: k for k, v in enums.AQR_DIMENSION_MAP.items()}
        measurements = Measurement.objects.filter(workshop = pk).all()

        ret = []

        for measurement in measurements:
            values = {v.dimension: v.value for v in measurement.values.all()}

            if measurement.participant is None or measurement.mode is None:
                continue
        
            data = {
                "time": measurement.time_measured.isoformat(),
                "device": measurement.device.id,  # or another unique identifier
                "participant": measurement.participant.name,
                "mode": measurement.mode.name,  # assumes user has a mode field
                "lat": None,
                "lon": None,
                "display_name": measurement.device.device_name if measurement.device.device_name is not None else measurement.device.id,
            }

            # Add dimension values
            for dim_id, name in aqr_reverse.items():
                if dim_id in values:
                    data[name] = values[dim_id]
                else:
                    data[name] = None

            # Add lat/lon if available
            if measurement.location and measurement.location.coordinates:
                data["lat"] = measurement.location.coordinates.y
                data["lon"] = measurement.location.coordinates.x
            
            ret.append(data)
        
        for record in AirQualityRecord.objects.filter(workshop = pk):
            data = {
                "time": record.time,
                "device": record.device.id,  # or another unique identifier
                "participant": record.participant.name,
                "mode": record.mode.name,  # assumes user has a mode field
                "lat": record.lat,
                "lon": record.lon,
                "display_name": record.device.device_name if record.device.device_name is not None else record.device.id,
                'pm1': record.pm1,
                'pm25': record.pm25,
                'pm10': record.pm10,
                'temperature': record.temperature,
                'humidity': record.humidity,
            }

            ret.append(data)

        return JsonResponse(ret, status=200, safe=False)


@extend_schema(tags=['devices'])
class CreateStationStatusAPIView(APIView):
    serializer_class = StationStatusSerializer 
    def post(self, request, *args, **kwargs):
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

            return Response({"status": "success"}, status=200)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['devices'])
class CreateStationDataAPIView(APIView):
    serializer_class = StationDataSerializer 
    def post(self, request, *args, **kwargs):
        # Parse the incoming JSON data
        try:
            station_data = request.data.get('station', None)
            sensors_data = request.data.get('sensors', None)

            if not station_data:
                raise ValidationError("Both 'station' and 'sensors' are required.")

            # Use the get_or_create_station function to get or create the station
            station = get_or_create_station(station_data)

            if station.api_key != station_data.get('apikey'):
                raise ValidationError("Wrong API Key")

            # Record the time when the request was received
            time_received = datetime.now(timezone.utc)

            if sensors_data is None:
                return JsonResponse({"status": "success, but no sensor data found"}, status=200)

            try:
                with transaction.atomic():
                    # Iterate through all sensors
                    for sensor_id, sensor_data in sensors_data.items():
                        # Check if the measurement already exists in the database
                        existing_measurement = Measurement.objects.filter(
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
                        measurement = Measurement(
                            sensor_model=sensor_data['type'],
                            device=station,
                            time_measured=station_data['time'],
                            time_received=time_received,
                            room = station.current_room,
                            user = station.current_user,
                        )

                        if 'workshop' in station_data:
                            measurement.workshop = Workshop.objects.filter(name = station_data['workshop']).first()

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

                    return JsonResponse({"status": "success"}, status=200)

            except Exception as e:
                import traceback
                print(traceback.format_exc())
                return JsonResponse({"status": "error", "message": str(e)}, status=400)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
