"""Serializers for air quality records API."""
from collections.abc import Mapping

from rest_framework import serializers

from api.models import AirQualityRecord


class AirQualityRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirQualityRecord
        fields = "__all__"


class AirQualityRecordWorkshopSerializer(serializers.ModelSerializer):
    device_name = serializers.SerializerMethodField()

    class Meta:
        model = AirQualityRecord
        fields = [
            "time",
            "pm1",
            "pm25",
            "pm10",
            "temperature",
            "humidity",
            "lat",
            "lon",
            "device_name",
            "participant",
            "mode",
        ]

    def get_device_name(self, obj):
        device = getattr(obj, "device", None)
        if device:
            return device.device_name or device.id
        if isinstance(obj, Mapping):
            return obj.get("device")
        return None
