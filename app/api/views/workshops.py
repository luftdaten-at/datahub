"""Views for workshop and workshop air quality API (detail, data GET, air quality add)."""
import logging
from django.db import IntegrityError
from django.utils.dateparse import parse_datetime
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from devices.models import Device, Measurement
from main import enums
from api.models import AirQualityRecord
from workshops.models import Participant, Workshop
from api.models import MobilityMode

from api.serializers import (
    AirQualityRecordSerializer,
    AirQualityRecordWorkshopSerializer,
    WorkshopSerializer,
)

logger = logging.getLogger("myapp")


@extend_schema(
    tags=["workshops"],
    summary="Add air quality data",
    description="Adds one or more air quality records to a workshop. Creates or retrieves related Device, Participant, and MobilityMode objects as needed. Records must be within the workshop timeframe. Accepts a JSON array of records.",
    request=AirQualityRecordSerializer(many=True),
    responses={
        201: {"description": "Records created successfully"},
        400: {"description": "Validation errors - check errors array for details"},
    },
    examples=[
        OpenApiExample(
            "Add single record",
            value=[
                {
                    "time": "2026-01-15T13:45:39.889337Z",
                    "device": "28372F821AE5",
                    "participant": "Air Around 0007",
                    "mode": "walking",
                    "workshop": "homrh8",
                    "pm1": 33.8,
                    "pm25": 36.3,
                    "pm10": 37.4,
                    "temperature": 22.2,
                    "humidity": 39.2,
                    "voc": 15.0,
                    "lat": 48.1769523,
                    "lon": 16.3654834,
                }
            ],
            request_only=True,
        )
    ],
)
class AirQualityDataAddView(APIView):
    serializer_class = AirQualityRecordSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Expected a list of records"}, status=status.HTTP_400_BAD_REQUEST)

        records = []
        errors = []
        for record in data:
            try:
                device_str = record.get("device")
                if not device_str:
                    errors.append({"error": "Device field is required"})
                    continue
                mac = device_str.upper()
                rmac = "".join(reversed([mac[i : i + 2] for i in range(0, len(mac), 2)]))
                device_id = f"{rmac}AAA"

                device, _ = Device.objects.get_or_create(id=device_id)
                participant, _ = Participant.objects.get_or_create(name=record.get("participant"))
                mode, _ = MobilityMode.objects.get_or_create(name=record.get("mode"))
                workshop = Workshop.objects.get(name=record.get("workshop"))
                time = parse_datetime(record.get("time"))

                if AirQualityRecord.objects.filter(time=time, device=device).exists():
                    errors.append({"error": f"Record with time {time} and device {device.id} already exists"})
                    continue

                if not (workshop.start_date <= time <= workshop.end_date):
                    errors.append({"error": f"The time {time} of the record is not within the start and end date of the workshop."})
                    continue

                air_quality_data = {
                    **record,
                    "device": device,
                    "workshop": record.get("workshop"),
                    "participant": participant,
                    "mode": mode,
                }

                serializer = AirQualityRecordSerializer(data=air_quality_data)
                if serializer.is_valid():
                    serializer.save()
                    records.append(serializer.data)
                    workshop_name = record.get("workshop")
                    if workshop_name:
                        cache_key = f"workshop_data_{workshop_name}"
                        cache.delete(cache_key)
                        logger.info(f"Invalidated cache for workshop {workshop_name}")
                else:
                    errors.append(serializer.errors)
            except Workshop.DoesNotExist:
                errors.append({"error": "Workshop not found"})
            except IntegrityError as e:
                errors.append({"error": str(e)})

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(records, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["workshops"],
    summary="Get workshop details",
    description="Retrieves detailed information about a specific workshop including title, description, dates, and settings.",
    parameters=[
        OpenApiParameter(
            name="pk",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Workshop name (primary key)",
            required=True,
            examples=[OpenApiExample("Example workshop", value="homrh8")],
        )
    ],
    responses={200: WorkshopSerializer, 404: {"description": "Workshop not found"}},
)
class WorkshopDetailView(RetrieveAPIView):
    queryset = Workshop.objects.all()
    serializer_class = WorkshopSerializer


@extend_schema(
    tags=["workshops"],
    summary="Add air quality data",
    description="**Legacy.** Use POST /api/v1/workshops/data/add/ instead. Adds one or more air quality records to a workshop.",
    deprecated=True,
)
class LegacyAirQualityDataAddView(AirQualityDataAddView):
    """Root-level /api/workshop/data/add/ – prefer /api/v1/workshops/data/add/."""


@extend_schema(
    tags=["workshops"],
    summary="Get workshop details",
    description="**Legacy.** Use GET /api/v1/workshops/{pk}/ instead. Retrieves detailed information about a specific workshop.",
    deprecated=True,
)
class LegacyWorkshopDetailView(WorkshopDetailView):
    """Root-level /api/workshop/detail/{pk}/ – prefer /api/v1/workshops/{pk}/."""


@extend_schema(
    tags=["workshops"],
    summary="Get workshop air quality data",
    description="Retrieves all air quality measurement data for a workshop. Returns data from both the Measurement model (new) and AirQualityRecord model (legacy). Records without participant or mode use '—' as placeholder.",
    parameters=[
        OpenApiParameter(
            name="pk",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Workshop name (primary key)",
            required=True,
            examples=[OpenApiExample("Example workshop", value="homrh8")],
        )
    ],
    responses={
        200: {"description": "List of air quality records with sensor measurements and location data"},
        404: {"description": "Workshop not found"},
    },
)
class WorkshopAirQualityDataView(RetrieveAPIView):
    queryset = AirQualityRecord.objects.all()
    serializer_class = AirQualityRecordWorkshopSerializer

    def get(self, request, pk):
        cache_key = f"workshop_data_{pk}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Workshop {pk}: Returning cached data")
            return JsonResponse(cached_data, status=200, safe=False)

        try:
            workshop_obj = Workshop.objects.get(name=pk)
        except Workshop.DoesNotExist:
            return JsonResponse({"error": "Workshop not found"}, status=404)

        aqr_reverse = {v: k for k, v in enums.AQR_DIMENSION_MAP.items()}
        measurements = Measurement.objects.filter(workshop=workshop_obj).all()

        ret = []
        logger.info(f"Workshop {pk}: Found {measurements.count()} measurements, {AirQualityRecord.objects.filter(workshop=workshop_obj).count()} AirQualityRecords")

        for measurement in measurements:
            values = {v.dimension: v.value for v in measurement.values.all()}

            data = {
                "time": measurement.time_measured.isoformat(),
                "device": measurement.device.id,
                "participant": measurement.participant.name if measurement.participant else "—",
                "mode": measurement.mode.name if measurement.mode else "—",
                "lat": None,
                "lon": None,
                "display_name": measurement.device.device_name if measurement.device.device_name is not None else measurement.device.id,
            }
            for dim_id, name in aqr_reverse.items():
                data[name] = values[dim_id] if dim_id in values else None
            if measurement.location and measurement.location.coordinates:
                data["lat"] = measurement.location.coordinates.y
                data["lon"] = measurement.location.coordinates.x
            ret.append(data)

        air_quality_records = AirQualityRecord.objects.filter(workshop=workshop_obj).select_related("device", "participant", "mode")
        logger.info(f"Workshop {pk}: Processing {air_quality_records.count()} AirQualityRecords")

        for record in air_quality_records:
            device_name = None
            if record.device:
                device_id = record.device.id if hasattr(record.device, "id") else str(record.device)
                try:
                    device = Device.objects.get(id=device_id)
                    if device.device_name:
                        device_name = device.device_name
                    else:
                        if device_id and len(device_id) >= 3 and device_id.endswith("AAA"):
                            try:
                                base_id = device_id[:-3]
                                if len(base_id) > 0:
                                    last_char = base_id[-1]
                                    try:
                                        last_char_int = int(last_char, 16)
                                        last_char_int = (last_char_int + 1) % 16
                                        corrected_last_char = format(last_char_int, "X")
                                        corrected_base = base_id[:-1] + corrected_last_char
                                        corrected_device_id = corrected_base + "AAA"
                                        corrected_device = Device.objects.get(id=corrected_device_id)
                                        device_name = corrected_device.device_name if corrected_device.device_name else corrected_device.id
                                        logger.info(f"Found device with corrected ID: {corrected_device_id} (original: {device_id})")
                                    except (ValueError, Device.DoesNotExist):
                                        device_name = device_id
                            except Exception as e:
                                logger.warning(f"Error correcting device ID {device_id}: {e}")
                                device_name = device_id
                        else:
                            device_name = device_id
                except Device.DoesNotExist:
                    if device_id and len(device_id) >= 3 and device_id.endswith("AAA"):
                        try:
                            base_id = device_id[:-3]
                            if len(base_id) > 0:
                                last_char = base_id[-1]
                                try:
                                    last_char_int = int(last_char, 16)
                                    last_char_int = (last_char_int + 1) % 16
                                    corrected_last_char = format(last_char_int, "X")
                                    corrected_base = base_id[:-1] + corrected_last_char
                                    corrected_device_id = corrected_base + "AAA"
                                    corrected_device = Device.objects.get(id=corrected_device_id)
                                    device_name = corrected_device.device_name if corrected_device.device_name else corrected_device.id
                                    logger.info(f"Found device with corrected ID: {corrected_device_id} (original: {device_id})")
                                except (ValueError, Device.DoesNotExist):
                                    device_name = device_id
                        except Exception as e:
                            logger.warning(f"Error correcting device ID {device_id}: {e}")
                            device_name = device_id
                    else:
                        device_name = device_id

            data = {
                "time": record.time.isoformat() if hasattr(record.time, "isoformat") else str(record.time),
                "device": device_name,
                "participant": record.participant.name if record.participant else "—",
                "mode": record.mode.name if record.mode else "—",
                "lat": record.lat,
                "lon": record.lon,
                "display_name": device_name,
                "pm1": record.pm1,
                "pm25": record.pm25,
                "pm10": record.pm10,
                "temperature": record.temperature,
                "humidity": record.humidity,
                "voc": record.voc,
                "nox": record.nox,
            }
            ret.append(data)

        cache.set(cache_key, ret, 900)
        logger.info(f"Workshop {pk}: Cached data for 15 minutes")
        return JsonResponse(ret, status=200, safe=False)
