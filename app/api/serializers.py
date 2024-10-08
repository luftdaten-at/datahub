from rest_framework import serializers
from .models import AirQualityRecord, AirQualityDatapoint, Measurement
from workshops.models import Workshop
from devices.models import Device, DeviceStatus, Sensor


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


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ['sensor', 'pm1', 'pm25', 'pm10', 'temperature', 'humidity', 'voc_index', 'nox_index', 'co2', 'o3', 'iaq_index', 'iaq_acc', 'iaq_static', 'pressure']

    def validate_sensor(self, value):
        # Try to get the sensor by name, create if does not exist
        sensor, create = Sensor.objects.get_or_create(name=value)
        return sensor

class AirQualityDatapointSerializer(serializers.ModelSerializer):
    measurements = MeasurementSerializer(many=True)

    class Meta:
        model = AirQualityDatapoint
        fields = ['time', 'device', 'campaign', 'workshop', 'participant', 'lat', 'lon', 'location_precision', 'mode', 'measurements']

    def create(self, validated_data):
        measurements_data = validated_data.pop('measurements', [])
        datapoint = AirQualityDatapoint.objects.create(**validated_data)
        for measurement_data in measurements_data:
            measurement_data['sensor'] = self.fields['measurements'].child.fields['sensor'].run_validation(measurement_data['sensor'])
            Measurement.objects.create(datapoint=datapoint, **measurement_data)
        return datapoint


class AirQualityRecordSerializer(serializers.ModelSerializer):    
    class Meta:
        model = AirQualityRecord
        fields = '__all__'


class WorkshopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = '__all__'