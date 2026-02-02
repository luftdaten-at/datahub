"""Serializers for workshop and workshop spots API."""
from rest_framework import serializers

from workshops.models import Workshop


class WorkshopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = "__all__"


class WorkshopSpotSerializer(serializers.Serializer):
    workshop = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    radius = serializers.FloatField()
    type = serializers.CharField()


class WorkshopSpotPkSerializer(serializers.Serializer):
    workshop = serializers.CharField()
    workshop_spot = serializers.IntegerField()
