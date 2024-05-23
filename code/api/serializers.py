from rest_framework import serializers
from .models import AirQualityRecord, AirQualityDatapoint, Measurement
from workshops.models import Workshop
from devices.models import Device, Sensor


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'

    def validate_device(self, value):
        # Try to get the sensor by id, create if does not exist
        device, create = Device.objects.get_or_create(id=value)
        return device
    

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