from rest_framework import serializers
from .models import AirQualityRecord
from workshops.models import Workshop
from devices.models import Device, DeviceStatus, Sensor
from django.utils import timezone

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'

    def validate_device(self, value):
        # Try to get the sensor by id, create if does not exist
        device, create = Device.objects.get_or_create(id=value)
        return device
    
class BatterySerializer(serializers.Serializer):
    voltage = serializers.FloatField()
    percentage = serializers.FloatField()

class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['name', 'product_type', 'serial', 'firmware', 'hardware', 'protocol']

class DeviceStatusSerializer(serializers.ModelSerializer):
    battery = BatterySerializer(write_only=True)
    sensors = SensorSerializer(many=True, write_only=True)

    class Meta:
        model = DeviceStatus
        fields = ['device', 'battery', 'sensors']

    def create(self, validated_data):
        battery_data = validated_data.pop('battery')
        sensors_data = validated_data.pop('sensors')

        # Get or create the device
        device, _ = Device.objects.get_or_create(id=validated_data['device'].id)
        
        # Create the device status
        device_status = DeviceStatus.objects.create(
            device=device,
            battery_voltage=battery_data['voltage'],
            battery_soc=battery_data['percentage'],
            sensors=sensors_data  # Storing sensors as JSON for simplicity
        )

        # Save each sensor (or update if it already exists)
        for sensor_data in sensors_data:
            Sensor.objects.update_or_create(
                name=sensor_data['name'],
                serial=sensor_data.get('serial', ''),
                defaults={
                    'product_type': sensor_data.get('product_type', ''),
                    'firmware': sensor_data.get('firmware', ''),
                    'hardware': sensor_data.get('hardware', ''),
                    'protocol': sensor_data.get('protocol', '')
                }
            )

        # Update the last_update field of the device to the current time
        device.last_update = timezone.now()
        device.save()

        return device_status


class AirQualityRecordSerializer(serializers.ModelSerializer):    
    class Meta:
        model = AirQualityRecord
        fields = '__all__'


class WorkshopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = '__all__'


# devices/data
'''JSON
"station": {
    {
        "time": "2025-01-07T11:23:23.439Z",
        "device": "string",
        "firmware": "string",
        "model": 0,
        "apikey": "123",
        "battery": {
            "voltage": 0,
            "percentage": 0
        }
    },
"sensors": {
    "1": { "type": 1, "data": { "2": 5.0, "3": 6.0, "5": 7.0, "6": 0.67, "7": 20.0, "8": 100 }},
    "2": { "type": 6, "data": { "6": 0.72, "7": 20.1 }}
}
'''
class SensorDataSerializer(serializers.Serializer):
    type = serializers.IntegerField()
    data = serializers.DictField(child=serializers.FloatField())


class BatteryDataSerializer(serializers.Serializer):
    voltage = serializers.FloatField()
    percentage = serializers.FloatField()


class StationInfoSerializer(serializers.Serializer):
    time = serializers.DateTimeField()
    device = serializers.CharField()
    firmware = serializers.CharField()
    model = serializers.IntegerField()
    battery = BatteryDataSerializer()
    apikey = serializers.CharField()


class StationDataSerializer(serializers.Serializer):
    station = StationInfoSerializer()
    sensors = serializers.DictField(child=SensorDataSerializer())


# devices/status
'''JSON
{
  "status_list": [
    {
      "time": "2025-01-07T11:06:21.222Z",
      "level": 0,
      "message": "string"
    }
  ]
}
'''
class StationStatusDataSerializer(serializers.Serializer):
    time = serializers.DateTimeField()
    level = serializers.IntegerField()
    message = serializers.CharField()


class StationStatusSerializer(serializers.Serializer):
    station_info = StationInfoSerializer()
    status_list = serializers.ListField(child=StationStatusDataSerializer())
