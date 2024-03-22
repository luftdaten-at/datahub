from rest_framework import serializers
from .models import AirQualityRecord, Location
from workshops.models import Workshop
#from devices.models import Device


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'


class AirQualityRecordSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)  # Nest the LocationSerializer
    
    class Meta:
        model = AirQualityRecord
        fields = '__all__'


class WorkshopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = '__all__'