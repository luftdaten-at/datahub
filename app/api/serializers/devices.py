"""Serializers for device API (status, data)."""
from django.utils import timezone
from rest_framework import serializers

from devices.models import Device, DeviceStatus, Sensor


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"

    def validate_device(self, value):
        device, create = Device.objects.get_or_create(id=value)
        return device


class BatterySerializer(serializers.Serializer):
    voltage = serializers.FloatField()
    percentage = serializers.FloatField()


class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ["name", "product_type", "serial", "firmware", "hardware", "protocol"]


class DeviceStatusSerializer(serializers.ModelSerializer):
    battery = BatterySerializer(write_only=True)
    sensors = SensorSerializer(many=True, write_only=True)

    class Meta:
        model = DeviceStatus
        fields = ["device", "battery", "sensors"]

    def create(self, validated_data):
        battery_data = validated_data.pop("battery")
        sensors_data = validated_data.pop("sensors")

        device, _ = Device.objects.get_or_create(id=validated_data["device"].id)

        device_status = DeviceStatus.objects.create(
            device=device,
            battery_voltage=battery_data["voltage"],
            battery_soc=battery_data["percentage"],
            sensors=sensors_data,
        )

        for sensor_data in sensors_data:
            Sensor.objects.update_or_create(
                name=sensor_data["name"],
                serial=sensor_data.get("serial", ""),
                defaults={
                    "product_type": sensor_data.get("product_type", ""),
                    "firmware": sensor_data.get("firmware", ""),
                    "hardware": sensor_data.get("hardware", ""),
                    "protocol": sensor_data.get("protocol", ""),
                },
            )

        device.last_update = timezone.now()
        device.save()

        return device_status


class SensorDataSerializer(serializers.Serializer):
    type = serializers.IntegerField()
    data = serializers.DictField(child=serializers.FloatField())


class BatteryDataSerializer(serializers.Serializer):
    voltage = serializers.FloatField()
    percentage = serializers.FloatField()


class DeviceInfoSerializer(serializers.Serializer):
    time = serializers.DateTimeField()
    device = serializers.CharField()
    firmware = serializers.CharField()
    model = serializers.IntegerField()
    battery = BatteryDataSerializer()
    apikey = serializers.CharField()


class DevicePayloadSerializer(serializers.Serializer):
    """Device block in POST /v1/devices/data/"""

    time = serializers.DateTimeField()
    id = serializers.CharField()
    firmware = serializers.CharField()
    model = serializers.IntegerField()
    apikey = serializers.CharField()


class WorkshopContextSerializer(serializers.Serializer):
    """Workshop context in POST /v1/devices/data/"""

    id = serializers.CharField()
    participant = serializers.CharField()
    mode = serializers.CharField()


class DeviceDataSerializer(serializers.Serializer):
    """Request body for POST /v1/devices/data/: device, workshop, sensors."""

    device = DevicePayloadSerializer()
    workshop = WorkshopContextSerializer()
    sensors = serializers.DictField(child=SensorDataSerializer())


class DeviceStatusLogSerializer(serializers.Serializer):
    time = serializers.DateTimeField()
    level = serializers.IntegerField()
    message = serializers.CharField()


class DeviceStatusRequestSerializer(serializers.Serializer):
    """Request body for POST /v1/devices/status/: device, status_list."""

    device = DeviceInfoSerializer()
    status_list = serializers.ListField(child=DeviceStatusLogSerializer())
