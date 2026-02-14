"""Views for device API (status, data, device detail)."""
import logging
from datetime import datetime, timezone
from django.db import transaction
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
from main.util import get_or_create_station
from api.models import Location, MobilityMode
from workshops.models import Participant, Workshop

from api.serializers import DeviceSerializer, DeviceDataSerializer, DeviceStatusRequestSerializer

logger = logging.getLogger("myapp")


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
    description="Adds status log entries for a device. Requires valid API key authentication. Updates device test_mode and calibration_mode flags.",
    request=DeviceStatusRequestSerializer,
    responses={
        200: {"description": "Status logs created successfully. Returns status and device flags."},
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
        device_data = request.data.get("device")
        status_list = request.data.get("status_list", [])

        if not device_data or not status_list:
            raise ValidationError("Both 'device' and 'status_list' are required.")

        device = get_or_create_station(station_info=device_data)

        if device.api_key != device_data.get("apikey"):
            raise ValidationError("Wrong API Key")

        if device.test_mode is None:
            device.test_mode = device_data.get("test_mode")
        if device.calibration_mode is None:
            device.calibration_mode = device_data.get("calibration_mode")
        device.save()

        try:
            with transaction.atomic():
                for status_data in status_list:
                    DeviceLogs.objects.create(
                        device=device,
                        timestamp=status_data["time"],
                        level=status_data.get("level", 1),
                        message=status_data.get("message", ""),
                    )

            return Response(
                {
                    "status": "success",
                    "flags": {
                        "test_mode": device.test_mode,
                        "calibration_mode": device.calibration_mode,
                    },
                },
                status=200,
            )

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["devices"],
    summary="Add device measurement data",
    description="Adds measurement data from sensors for a device. Request body: device, workshop, sensors. Optional location {lat, lon} in device block. Creates Measurement and Values records. Prevents duplicate measurements.",
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
            device_data = request.data.get("device")
            workshop_data = request.data.get("workshop")
            sensors_data = request.data.get("sensors")
            location_data = request.data.get("location")

            if not device_data:
                raise ValidationError("'device' is required.")
            if not workshop_data:
                raise ValidationError("'workshop' is required.")

            device_info = {
                "device": device_data["id"],
                "firmware": device_data.get("firmware", ""),
                "model": device_data.get("model"),
                "apikey": device_data.get("apikey"),
            }
            device = get_or_create_station(station_info=device_info)

            if device.api_key != device_data.get("apikey"):
                raise ValidationError("Wrong API Key")

            time_received = datetime.now(timezone.utc)
            time_measured = parse_datetime(device_data["time"])
            if not time_measured:
                raise ValidationError("Invalid device.time.")

            if not sensors_data:
                return JsonResponse({"status": "success, but no sensor data found"}, status=200)

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
                        point = Point(float(lon), float(lat))
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
                            location=location_obj,
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
