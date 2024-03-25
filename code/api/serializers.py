from rest_framework import serializers
from .models import AirQualityRecord
from workshops.models import Workshop
from devices.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'


class AirQualityRecordSerializer(serializers.ModelSerializer):    
    class Meta:
        model = AirQualityRecord
        fields = '__all__'


class WorkshopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = '__all__'