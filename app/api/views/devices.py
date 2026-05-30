"""Views for device API (status, data, device detail)."""
import logging
from datetime import datetime, timezone

from django.db import transaction
from django.utils import timezone as django_timezone
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from django.contrib.gis.geos import Point

from devices.models import Device, DeviceLogs, Measurement, Values
from devices.sensor_scan import parse_sensor_scan, sensor_list_from_model_ids
from main.util import get_or_create_station
from api.models import Location, MobilityMode
from workshops.models import Participant, Workshop

from api.serializers import DeviceSerializer, DeviceDataSerializer, DeviceStatusRequestSerializer

logger = logging.getLogger("myapp")


def extract_device_block(data):
    """Top-level 'device' or 'station' (firmware)."""
    return data.get("device") or data.get("station")


def device_id_from_block(block):
    """Data API uses 'id'; status/firmware use 'device'."""
    device_id = block.get("id") or block.get("device")
    if not device_id:
        raise ValidationError("Device block must include 'id' or 'device'.")
    return device_id


def extract_location(data, device_block):
    """Top-level location or nested under station."""
    loc = data.get("location") or (device_block or {}).get("location")
    if not loc:
        return None
    return loc


def _latest_status_list_level(status_list):
    """Level of the status_list entry with the greatest `time` (not necessarily last index)."""
    latest_dt = None
    latest_level = None
    for status_data in status_list:
        t_raw = status_data.get("time")
        if t_raw is None:
            continue
        if isinstance(t_raw, datetime):
            dt = t_raw
            if django_timezone.is_naive(dt):
                dt = django_timezone.make_aware(dt)
        else:
            dt = parse_datetime(str(t_raw))
        if dt is None:
            continue
        if latest_dt is None or dt > latest_dt:
            latest_dt = dt
            latest_level = status_data.get("level", 1)
    return latest_level


@extend_schema(
    tags=["devices"],
    summary="Get device details",
    description="Retrieves detailed information about a specific device including device name, model, firmware, and current assignments.",
    parameters=[
        OpenApiParameter(
            name="pk",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Device ID (primary key)",
            required=True,
            examples=[OpenApiExample("Example device", value="D83BDA6E37DDAAA")],
        )
    ],
    responses={200: DeviceSerializer, 404: {"description": "Device not found"}},
)
class DeviceDetailView(RetrieveAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer


@extend_schema(
    tags=["devices"],
    summary="Add device status logs",
    description=(
        "Adds status log entries for a device. Requires valid API key authentication. "
        "Updates device test_mode and calibration_mode flags. "
        "If the device has a configured log_level and the newest status_list line's level "
        "differs, the 200 response also includes log_level (integer) for the device to apply."
    ),
    request=DeviceStatusRequestSerializer,
    responses={
        200: {
            "description": (
                "Success: status, flags, and optionally log_level when server log_level "
                "differs from the latest incoming line's level."
            )
        },
        400: {"description": "Validation error - wrong API key or invalid data"},
    },
    examples=[
        OpenApiExample(
            "Add status logs",
            value={
                "device": {
                    "time": "2025-01-07T11:23:23.439Z",
                    "device": "D83BDA6E37DDAAA",
                    "firmware": "2.0",
                    "model": 1,
                    "apikey": "your-api-key-here",
                    "battery": {"voltage": 3.7, "percentage": 85.0},
                },
                "status_list": [
                    {"time": "2025-01-07T11:06:21.222Z", "level": 1, "message": "Device started successfully"},
                    {"time": "2025-01-07T11:06:22.222Z", "level": 0, "message": "Sensor calibration complete"},
                ],
            },
            request_only=True,
        )
    ],
)
class CreateDeviceStatusAPIView(APIView):
    serializer_class = DeviceStatusRequestSerializer

    def post(self, request, *args, **kwargs):
        device_data = extract_device_block(request.data)
        status_list = request.data.get("status_list", [])

        if not device_data:
            logger.warning("Device status 400: missing device block. Request body: %s", request.data)
            raise ValidationError("Device block ('device' or 'station') is required.")

        device, station_status = get_or_create_station(station_info=device_data)

        if device.api_key != device_data.get("apikey"):
            logger.warning("Device status 400: wrong API key. Request body: %s", request.data)
            raise ValidationError("Wrong API Key")

        if device.test_mode is None:
            device.test_mode = device_data.get("test_mode")
        if device.calibration_mode is None:
            device.calibration_mode = device_data.get("calibration_mode")
        device.save()

        try:
            if status_list:
                with transaction.atomic():
                    for status_data in status_list:
                        DeviceLogs.objects.create(
                            device=device,
                            timestamp=status_data["time"],
                            level=status_data.get("level", 1),
                            message=status_data.get("message", ""),
                        )

                    scan_parse = None
                    for status_data in status_list:
                        if status_data.get("level", 1) != 1:
                            continue
                        msg = status_data.get("message", "") or ""
                        parsed = parse_sensor_scan(msg)
                        if parsed is not None:
                            scan_parse = parsed
                    if scan_parse is not None:
                        station_status.sensor_list = sensor_list_from_model_ids(
                            scan_parse.model_ids,
                            previous=station_status.sensor_list,
                            serial_by_model=scan_parse.serial_by_model,
                        )
                        station_status.save(update_fields=["sensor_list"])

            device.refresh_from_db()
            payload = {
                "status": "success",
                "flags": {
                    "test_mode": device.test_mode,
                    "calibration_mode": device.calibration_mode,
                },
            }
            desired = device.log_level
            if desired is not None:
                latest_level = _latest_status_list_level(status_list)
                if latest_level is not None and latest_level != desired:
                    payload["log_level"] = desired

            return Response(payload, status=200)

        except Exception as e:
            logger.warning("Device status 400: %s. Request body: %s", str(e), request.data, exc_info=True)
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["devices"],
    summary="Add device measurement data",
    description="Adds measurement data from sensors for a device. Request body: device, sensors. Optional workshop (requires location when present), optional location {lat, lon}. Creates Measurement and Values records. Prevents duplicate measurements.",
    request=DeviceDataSerializer,
    responses={
        200: {"description": "Measurements created successfully, or no sensor data found"},
        400: {"description": "Validation error - wrong API key or invalid data"},
        422: {"description": "Duplicate measurement - measurement with same device, time, and sensor_model already exists"},
    },
    examples=[
        OpenApiExample(
            "Add measurement data",
            value={
                "device": {
                    "time": "2025-01-07T11:23:23.439Z",
                    "id": "D83BDA6E37DDAAA",
                    "firmware": "2.0.0",
                    "model": 1,
                    "apikey": "your-api-key-here",
                },
                "workshop": {"id": "homrh8", "participant": "8133a310-ffaf-11f0-8794-bbb756d19a96", "mode": "walking"},
                "location": {"lat": 48.1769523, "lon": 16.3654834},
                "sensors": {
                    "1": {"type": 1, "data": {"2": 5, "3": 6, "5": 7, "6": 0.67, "7": 20, "8": 100}},
                    "2": {"type": 6, "data": {"6": 0.72, "7": 20.1}},
                },
            },
            request_only=True,
        )
    ],
)
class CreateDeviceDataAPIView(APIView):
    serializer_class = DeviceDataSerializer

    def post(self, request, *args, **kwargs):
        try:
            device_data = extract_device_block(request.data)
            workshop_data = request.data.get("workshop")
            sensors_data = request.data.get("sensors")
            location_data = extract_location(request.data, device_data)

            if not device_data:
                raise ValidationError("Device block ('device' or 'station') is required.")
            if workshop_data and not location_data:
                raise ValidationError("'location' is required when 'workshop' is provided.")

            device_info = {
                "device": device_id_from_block(device_data),
                "firmware": device_data.get("firmware", ""),
                "model": device_data.get("model"),
                "apikey": device_data.get("apikey"),
            }
            device, _ = get_or_create_station(station_info=device_info)

            if device.api_key != device_data.get("apikey"):
                raise ValidationError("Wrong API Key")

            time_received = datetime.now(timezone.utc)
            time_measured = parse_datetime(device_data["time"])
            if not time_measured:
                raise ValidationError("Invalid device.time.")

            if not sensors_data:
                return JsonResponse({"status": "success, but no sensor data found"}, status=200)

            workshop_obj = None
            participant_obj = None
            mode_obj = None
            if workshop_data:
                workshop_obj = Workshop.objects.filter(name=workshop_data["id"]).first()
                participant_obj, _ = Participant.objects.get_or_create(
                    name=workshop_data["participant"],
                    defaults={"workshop": workshop_obj},
                )
                mode_name = workshop_data["mode"]
                mode_obj, _ = MobilityMode.objects.get_or_create(
                    name=mode_name,
                    defaults={"title": mode_name.title(), "description": ""},
                )

            lat = location_data.get("lat") if location_data else None
            lon = location_data.get("lon") if location_data else None

            try:
                with transaction.atomic():
                    # Create location if lat/lon provided (same as workshops/data/add)
                    location_obj = None
                    if lat is not None and lon is not None:
                        point = Point(float(lon), float(lat), srid=4326)
                        location_obj = Location.objects.create(coordinates=point)
                    for sensor_id, sensor_data in sensors_data.items():
                        existing_measurement = Measurement.objects.filter(
                            device=device,
                            time_measured=time_measured,
                            sensor_model=sensor_data["type"],
                        ).first()

                        if existing_measurement:
                            return JsonResponse(
                                {"status": "error", "detail": "Measurement already in Database"},
                                status=422,
                            )

                        measurement = Measurement(
                            sensor_model=sensor_data["type"],
                            device=device,
                            time_measured=time_measured,
                            time_received=time_received,
                            room=device.current_room,
                            user=device.current_user,
                            workshop=workshop_obj,
                            participant=participant_obj,
                            mode=mode_obj,
                            location_id=location_obj.pk if location_obj else None,
                        )
                        measurement.save()

                        for dimension, value in sensor_data["data"].items():
                            Values.objects.create(
                                dimension=int(dimension),
                                value=float(value),
                                measurement=measurement,
                            )

                    device.last_update = time_measured
                    device.save()

                    return JsonResponse({"status": "success"}, status=200)

            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=400)

        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
