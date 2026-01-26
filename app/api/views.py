import logging
import json
from datetime import datetime, timezone
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime
from django.contrib.gis.geos import Point
from django.core.cache import cache

from devices.models import DeviceLogs, Measurement, Values
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from main.util import get_or_create_station, get_avg_temp_per_spot
from .models import AirQualityRecord, MobilityMode
from workshops.models import Participant, Workshop, WorkshopSpot
from devices.models import Device
from main import enums

from .serializers import AirQualityRecordSerializer, AirQualityRecordWorkshopSerializer, DeviceSerializer, WorkshopSerializer, StationDataSerializer, StationStatusSerializer, WorkshopSpotSerializer, WorkshopSpotPkSerializer

logger = logging.getLogger('myapp')


@extend_schema(
    tags=['workshops'],
    summary='Create a workshop spot',
    description='Creates a new hot or cool spot (circle) on a workshop map. Requires authentication and workshop owner permissions.',
    request=WorkshopSpotSerializer,
    responses={
        201: {'description': 'Spot created successfully'},
        400: {'description': 'Invalid request data'},
        403: {'description': 'Permission denied - user is not the workshop owner'},
        404: {'description': 'Workshop not found'}
    },
    examples=[
        OpenApiExample(
            'Create hot spot',
            value={
                'workshop': 'homrh8',
                'lat': 48.2112,
                'lon': 16.3736,
                'radius': 100.0,
                'type': 'hot'
            },
            request_only=True
        ),
        OpenApiExample(
            'Create cool spot',
            value={
                'workshop': 'homrh8',
                'lat': 48.2200,
                'lon': 16.3800,
                'radius': 150.0,
                'type': 'cool'
            },
            request_only=True
        )
    ]
)
class CreateWorkshopSpotAPIView(APIView):
    """
    Creates a new workshop spot (hot or cool area) on the map.
    
    The spot is defined by a center point (latitude, longitude) and a radius in meters.
    The type can be either 'hot' or 'cool' to indicate temperature zones.
    """
    serializer_class = WorkshopSpotSerializer
    permission_classes = (IsAuthenticated,)
    def post(self, request, *args, **kwargs):
        j = request.data
        workshop = Workshop.objects.filter(pk=j['workshop']).first()
        if workshop is None:
            raise ValidationError("Workshop doesn't exists")
        if not (request.user.is_superuser or request.user == workshop.owner):
            raise PermissionDenied("You don't have the permissions to add a spot to this workshop")

        center = Point(j['lon'], j['lat'], srid=4326)
        center.transform(3857) # Web Mercator projection in meters
        circle_polygon = center.buffer(j['radius'], quadsegs=32)
        circle_polygon.transform(4326)

        WorkshopSpot.objects.get_or_create(
            workshop = workshop,
            center = center,
            radius = j['radius'],
            area = circle_polygon,
            type = j['type'],
        )

        return Response(status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['workshops'],
    summary='Delete a workshop spot',
    description='Deletes an existing workshop spot. Requires authentication and workshop owner permissions.',
    request=WorkshopSpotPkSerializer,
    responses={
        200: {'description': 'Spot deleted successfully'},
        400: {'description': 'Invalid request data'},
        403: {'description': 'Permission denied - user is not the workshop owner'},
        404: {'description': 'Workshop or workshop spot not found'}
    },
    examples=[
        OpenApiExample(
            'Delete spot',
            value={
                'workshop': 'homrh8',
                'workshop_spot': 123
            },
            request_only=True
        )
    ]
)
class DeleteWorkshopSpotAPIView(APIView):
    """
    Deletes an existing workshop spot by its primary key.
    
    Requires the workshop name and the workshop spot ID (pk).
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = WorkshopSpotPkSerializer 
    def post(self, request, *args, **kwargs):
        j = request.data
        workshop = Workshop.objects.filter(pk=j['workshop']).first()
        if workshop is None:
            raise ValidationError("Workshop doesn't exists")
        if not (request.user.is_superuser or request.user == workshop.owner):
            raise PermissionDenied("You don't have the permissions to add a spot to this workshop")

        workshop_spot = WorkshopSpot.objects.filter(pk = j['workshop_spot']).first()

        if workshop_spot is None:
            raise ValidationError("Workshop spot doesn't exists")

        workshop_spot.delete()

        return Response(status=status.HTTP_200_OK)


@extend_schema(
    tags=['workshops'],
    summary='Get workshop spots',
    description='Retrieves all spots (hot and cool areas) for a specific workshop, including their average temperatures.',
    parameters=[
        OpenApiParameter(
            name='pk',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Workshop name (primary key)',
            required=True,
            examples=[
                OpenApiExample('Example workshop', value='homrh8')
            ]
        )
    ],
    responses={
        200: {
            'description': 'List of workshop spots with coordinates, radius, type, and average temperature'
        },
        400: {'description': 'Invalid workshop name'},
        404: {'description': 'Workshop not found'}
    }
)
class GetWorkshopSpotsAPIView(APIView):
    """
    Retrieves all spots for a workshop.
    
    Returns a list of spots with their coordinates, radius, type (hot/cool),
    and average temperature calculated from measurements within the spot area.
    """
    serializer_class = WorkshopSpotPkSerializer 
    def get(self, request, pk, *args, **kwargs):
        workshop = Workshop.objects.filter(pk=pk).first()
        if workshop is None:
            raise ValidationError("Workshop doesn't exists")

        mean_temperature = {ws_id:mean_temp for ws_id, mean_temp in get_avg_temp_per_spot(pk)}
        ret = []
        for workshop_spot in workshop.workshop_spots.all():
            ret.append({
                'pk': workshop_spot.pk,
                'lon': workshop_spot.center.x,
                'lat': workshop_spot.center.y,
                'radius': workshop_spot.radius,
                'type': workshop_spot.type,
                'temperature': mean_temperature.get(workshop_spot.id, None)
            })

        return JsonResponse(ret, status=200, safe=False)


@extend_schema(
    tags=['workshops'],
    summary='Add air quality data',
    description='Adds one or more air quality records to a workshop. Creates or retrieves related Device, Participant, and MobilityMode objects as needed. Records must be within the workshop timeframe. Accepts a JSON array of records.',
    request=AirQualityRecordSerializer(many=True),
    responses={
        201: {'description': 'Records created successfully'},
        400: {'description': 'Validation errors - check errors array for details'}
    },
    examples=[
        OpenApiExample(
            'Add single record',
            value=[
                {
                    'time': '2026-01-15T13:45:39.889337Z',
                    'device': '28372F821AE5',
                    'participant': 'Air Around 0007',
                    'mode': 'walking',
                    'workshop': 'homrh8',
                    'pm1': 33.8,
                    'pm25': 36.3,
                    'pm10': 37.4,
                    'temperature': 22.2,
                    'humidity': 39.2,
                    'voc': 15.0,
                    'lat': 48.1769523,
                    'lon': 16.3654834
                }
            ],
            request_only=True
        )
    ]
)
class AirQualityDataAddView(APIView):
    """
    Adds air quality measurement records to a workshop.
    
    Accepts a list of air quality records. Each record must include:
    - time: ISO 8601 datetime string
    - device: Device identifier (MAC address will be converted to device ID)
    - participant: Participant name
    - mode: Mobility mode (e.g., 'walking', 'cycling')
    - workshop: Workshop name
    
    Optional fields: pm1, pm25, pm10, temperature, humidity, voc, nox, lat, lon
    
    Records are validated to ensure:
    - They are within the workshop's start and end dates
    - No duplicate records (same time and device)
    - Required fields are present
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
                device_str = record.get('device')
                if not device_str:
                    errors.append({'error': 'Device field is required'})
                    continue
                mac = device_str.upper()
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
                    # Invalidate cache for this workshop when new data is added
                    workshop_name = record.get('workshop')
                    if workshop_name:
                        cache_key = f'workshop_data_{workshop_name}'
                        cache.delete(cache_key)
                        logger.info(f"Invalidated cache for workshop {workshop_name}")
                else:
                    errors.append(serializer.errors)
            except Workshop.DoesNotExist:
                errors.append({'error': 'Workshop not found'})
            except IntegrityError as e:
                errors.append({'error': str(e)})

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(records, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['devices'],
    summary='Get device details',
    description='Retrieves detailed information about a specific device including device name, model, firmware, and current assignments.',
    parameters=[
        OpenApiParameter(
            name='pk',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Device ID (primary key)',
            required=True,
            examples=[
                OpenApiExample('Example device', value='D83BDA6E37DDAAA')
            ]
        )
    ],
    responses={
        200: DeviceSerializer,
        404: {'description': 'Device not found'}
    }
)
class DeviceDetailView(RetrieveAPIView):
    """
    Retrieves detailed information about a device.
    
    Returns all device fields including:
    - Identification: id, device_name
    - Hardware: model, firmware, btmac_address
    - Status: test_mode, calibration_mode, last_update
    - Assignments: current_room, current_organization, current_user, current_campaign
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer


@extend_schema(
    tags=['workshops'],
    summary='Get workshop details',
    description='Retrieves detailed information about a specific workshop including title, description, dates, and settings.',
    parameters=[
        OpenApiParameter(
            name='pk',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Workshop name (primary key)',
            required=True,
            examples=[
                OpenApiExample('Example workshop', value='homrh8')
            ]
        )
    ],
    responses={
        200: WorkshopSerializer,
        404: {'description': 'Workshop not found'}
    }
)
class WorkshopDetailView(RetrieveAPIView):
    """
    Retrieves detailed information about a workshop.
    
    Returns all workshop fields including:
    - Basic info: name, title, description
    - Dates: start_date, end_date
    - Settings: public, heat_hotspots_enabled
    - Map boundaries: mapbox coordinates
    - Relations: owner, users
    """
    queryset = Workshop.objects.all()
    serializer_class = WorkshopSerializer


@extend_schema(
    tags=['workshops'],
    summary='Get workshop air quality data',
    description='Retrieves all air quality measurement data for a workshop. Returns data from both the Measurement model (new) and AirQualityRecord model (legacy). Records without participant or mode are excluded.',
    parameters=[
        OpenApiParameter(
            name='pk',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Workshop name (primary key)',
            required=True,
            examples=[
                OpenApiExample('Example workshop', value='homrh8')
            ]
        )
    ],
    responses={
        200: {
            'description': 'List of air quality records with sensor measurements and location data'
        },
        404: {'description': 'Workshop not found'}
    }
)
class WorkshopAirQualityDataView(RetrieveAPIView):
    """
    Retrieves all air quality data for a workshop.
    
    Combines data from:
    - Measurement model (new format with dimension-based values)
    - AirQualityRecord model (legacy format with direct fields)
    
    Only includes records that have both participant and mode assigned.
    Device names are resolved, with automatic correction for device IDs ending in "AAA".
    
    Returns a JSON array of records with all available sensor dimensions.
    """
    queryset = AirQualityRecord.objects.all()
    serializer_class = AirQualityRecordWorkshopSerializer

    def get(self, request, pk):
        '''
        records = AirQualityRecord.objects.filter(workshop__name=pk)
        serializer = AirQualityRecordWorkshopSerializer(records, many=True)

        return Response(serializer.data)
        '''

        # Check cache first
        cache_key = f'workshop_data_{pk}'
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Workshop {pk}: Returning cached data")
            return JsonResponse(cached_data, status=200, safe=False)

        # Get the workshop object by name (pk is the workshop name)
        try:
            workshop_obj = Workshop.objects.get(name=pk)
        except Workshop.DoesNotExist:
            return JsonResponse({'error': 'Workshop not found'}, status=404)

        aqr_reverse = {v: k for k, v in enums.AQR_DIMENSION_MAP.items()}
        measurements = Measurement.objects.filter(workshop=workshop_obj).all()

        ret = []
        
        # Debug: Log counts
        logger.info(f"Workshop {pk}: Found {measurements.count()} measurements, {AirQualityRecord.objects.filter(workshop=workshop_obj).count()} AirQualityRecords")

        for measurement in measurements:
            values = {v.dimension: v.value for v in measurement.values.all()}

            if measurement.participant is None or measurement.mode is None:
                logger.debug(f"Skipping measurement {measurement.id}: participant={measurement.participant}, mode={measurement.mode}")
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
        
        air_quality_records = AirQualityRecord.objects.filter(workshop=workshop_obj).select_related('device', 'participant', 'mode')
        logger.info(f"Workshop {pk}: Processing {air_quality_records.count()} AirQualityRecords")
        
        for record in air_quality_records:
            # Skip records without participant or mode (similar to Measurement filtering)
            # But log them for debugging
            if record.participant is None:
                logger.warning(f"AirQualityRecord {record.id} has no participant")
            if record.mode is None:
                logger.warning(f"AirQualityRecord {record.id} has no mode")
            if record.participant is None or record.mode is None:
                # Still skip but log the issue
                logger.info(f"Skipping AirQualityRecord {record.id}: participant={record.participant}, mode={record.mode}, device={record.device}, time={record.time}")
                continue
            
            # Get device name - fetch device by id to get device_name
            # The record.device might only have the id, so we need to look up the full device object
            # If device ID ends with "AAA" and device doesn't have device_name, try correcting it
            device_name = None
            if record.device:
                device_id = record.device.id if hasattr(record.device, 'id') else str(record.device)
                try:
                    # First try with the original device ID
                    device = Device.objects.get(id=device_id)
                    # If device has a device_name, use it
                    if device.device_name:
                        device_name = device.device_name
                    else:
                        # Device found but no device_name, try correction if ID ends with "AAA"
                        if device_id and len(device_id) >= 3 and device_id.endswith("AAA"):
                            try:
                                # Remove last 3 characters "AAA"
                                base_id = device_id[:-3]
                                if len(base_id) > 0:
                                    # Get the last character and increment hex by 1
                                    last_char = base_id[-1]
                                    try:
                                        # Convert last char to int (hex), increment, convert back to hex
                                        last_char_int = int(last_char, 16)
                                        last_char_int = (last_char_int + 1) % 16  # Wrap around if needed
                                        corrected_last_char = format(last_char_int, 'X')
                                        # Replace last character
                                        corrected_base = base_id[:-1] + corrected_last_char
                                        corrected_device_id = corrected_base + "AAA"
                                        
                                        # Try to find device with corrected ID
                                        corrected_device = Device.objects.get(id=corrected_device_id)
                                        device_name = corrected_device.device_name if corrected_device.device_name else corrected_device.id
                                        logger.info(f"Found device with corrected ID: {corrected_device_id} (original: {device_id})")
                                    except (ValueError, Device.DoesNotExist):
                                        # If correction fails, fallback to original device id
                                        device_name = device_id
                            except Exception as e:
                                logger.warning(f"Error correcting device ID {device_id}: {e}")
                                device_name = device_id
                        else:
                            # No device_name and can't correct, use device id
                            device_name = device_id
                except Device.DoesNotExist:
                    # Device not found, try correction if ID ends with "AAA"
                    if device_id and len(device_id) >= 3 and device_id.endswith("AAA"):
                        try:
                            # Remove last 3 characters "AAA"
                            base_id = device_id[:-3]
                            if len(base_id) > 0:
                                # Get the last character and increment hex by 1
                                last_char = base_id[-1]
                                try:
                                    # Convert last char to int (hex), increment, convert back to hex
                                    last_char_int = int(last_char, 16)
                                    last_char_int = (last_char_int + 1) % 16  # Wrap around if needed
                                    corrected_last_char = format(last_char_int, 'X')
                                    # Replace last character
                                    corrected_base = base_id[:-1] + corrected_last_char
                                    corrected_device_id = corrected_base + "AAA"
                                    
                                    # Try to find device with corrected ID
                                    corrected_device = Device.objects.get(id=corrected_device_id)
                                    device_name = corrected_device.device_name if corrected_device.device_name else corrected_device.id
                                    logger.info(f"Found device with corrected ID: {corrected_device_id} (original: {device_id})")
                                except (ValueError, Device.DoesNotExist):
                                    # If correction fails, fallback to original device id
                                    device_name = device_id
                        except Exception as e:
                            logger.warning(f"Error correcting device ID {device_id}: {e}")
                            device_name = device_id
                    else:
                        # Device not found and can't correct, use device id
                        device_name = device_id
            else:
                device_name = None
                
            data = {
                "time": record.time.isoformat() if hasattr(record.time, 'isoformat') else str(record.time),
                "device": device_name,
                "participant": record.participant.name if record.participant else None,
                "mode": record.mode.name if record.mode else None,
                "lat": record.lat,
                "lon": record.lon,
                "display_name": device_name,
                'pm1': record.pm1,
                'pm25': record.pm25,
                'pm10': record.pm10,
                'temperature': record.temperature,
                'humidity': record.humidity,
                'voc': record.voc,
                'nox': record.nox,
            }

            ret.append(data)

        # Cache the result for 15 minutes (900 seconds)
        cache.set(cache_key, ret, 900)
        logger.info(f"Workshop {pk}: Cached data for 15 minutes")

        return JsonResponse(ret, status=200, safe=False)


@extend_schema(
    tags=['devices'],
    summary='Add station status logs',
    description='Adds status log entries for a station/device. Requires valid API key authentication. Updates device test_mode and calibration_mode flags.',
    request=StationStatusSerializer,
    responses={
        200: {'description': 'Status logs created successfully. Returns status and device flags.'},
        400: {'description': 'Validation error - wrong API key or invalid data'}
    },
    examples=[
        OpenApiExample(
            'Add status logs',
            value={
                'station': {
                    'time': '2025-01-07T11:23:23.439Z',
                    'device': 'D83BDA6E37DDAAA',
                    'firmware': '2.0',
                    'model': 1,
                    'apikey': 'your-api-key-here',
                    'battery': {
                        'voltage': 3.7,
                        'percentage': 85.0
                    }
                },
                'status_list': [
                    {
                        'time': '2025-01-07T11:06:21.222Z',
                        'level': 1,
                        'message': 'Device started successfully'
                    },
                    {
                        'time': '2025-01-07T11:06:22.222Z',
                        'level': 0,
                        'message': 'Sensor calibration complete'
                    }
                ]
            },
            request_only=True
        )
    ]
)
class CreateStationStatusAPIView(APIView):
    """
    Adds status log entries for a station/device.
    
    Accepts:
    - station: Station information including device ID, API key, battery status
    - status_list: Array of status log entries with timestamp, level, and message
    
    Validates API key and updates device flags (test_mode, calibration_mode).
    Creates DeviceLogs entries for each status in the list.
    """
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

        if station.test_mode is None:
            station.test_mode = station_data.get('test_mode')
        if station.calibration_mode is None:
            station.calibration_mode = station_data.get('calibration_mode')
        station.save()

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

            return Response(
                {
                    "status": "success",
                    "flags": {
                        "test_mode": station.test_mode,
                        "calibration_mode": station.calibration_mode,
                    }
                }, 
                status=200
            )

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['devices'],
    summary='Add station measurement data',
    description='Adds measurement data from sensors for a station/device. Requires valid API key authentication. Creates Measurement and Values records. Prevents duplicate measurements.',
    request=StationDataSerializer,
    responses={
        200: {'description': 'Measurements created successfully, or no sensor data found'},
        400: {'description': 'Validation error - wrong API key or invalid data'},
        422: {'description': 'Duplicate measurement - measurement with same device, time, and sensor_model already exists'}
    },
    examples=[
        OpenApiExample(
            'Add measurement data',
            value={
                'station': {
                    'time': '2025-01-07T11:23:23.439Z',
                    'device': 'D83BDA6E37DDAAA',
                    'firmware': '2.0',
                    'model': 1,
                    'apikey': 'your-api-key-here',
                    'workshop': 'homrh8'
                },
                'sensors': {
                    '1': {
                        'type': 1,
                        'data': {
                            '2': 5.0,  # PM1.0
                            '3': 6.0,  # PM2.5
                            '5': 7.0,  # PM10.0
                            '6': 0.67, # Humidity
                            '7': 20.0, # Temperature
                            '8': 100   # VOC Index
                        }
                    },
                    '2': {
                        'type': 6,
                        'data': {
                            '6': 0.72, # Humidity
                            '7': 20.1  # Temperature
                        }
                    }
                }
            },
            request_only=True
        )
    ]
)
class CreateStationDataAPIView(APIView):
    """
    Adds measurement data from sensors for a station/device.
    
    Accepts:
    - station: Station information including device ID, API key, timestamp, optional workshop
    - sensors: Dictionary of sensor data, keyed by sensor ID
    
    Each sensor entry contains:
    - type: Sensor model ID
    - data: Dictionary mapping dimension IDs to values
    
    Validates API key and prevents duplicate measurements (same device, time, sensor_model).
    Creates Measurement records and associated Values for each dimension.
    Updates station's last_update timestamp.
    """
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
                (traceback.format_exc())
                return JsonResponse({"status": "error", "message": str(e)}, status=400)

        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            return JsonResponse({"status": "error", "message": str(e)}, status=400)



