from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.test import TestCase
from .models import Device, Workshop, Location, AirQualityRecord
from .serializers import AirQualityRecordSerializer

class AirQualityDataTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create initial objects required for the test
        self.device = Device.objects.create(name="B040")
        self.workshop = Workshop.objects.create(id="i7847g", title="Test Workshop",start_date="2019-01-01T00:00:00+00:00", end_date="2019-01-01T00:00:00+00:00")
        self.location_data = {
            "lat": 51.509865,
            "lon": -0.118092,
            "precision": 10
        }
        self.location = Location.objects.create(**self.location_data)

        self.valid_payload = [{
            "time": "2019-01-01T00:00:00+00:00",
            "pm1": 10,
            "pm25": 20,
            "pm10": 30,
            "temperature": 20,
            "humidity": 50,
            "voc": 100,
            "nox": 200,
            "device": "B040",
            "workshop": "i7847g",
            "location": self.location_data
        }]

        self.invalid_payload = [{
            # This payload lacks the required 'time' field
            "pm1": 10,
            "pm25": 20,
        }]

    def test_create_air_quality_records(self):
        response = self.client.post(reverse('api-air-quality-data-add'), 
                                    data=self.valid_payload, 
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AirQualityRecord.objects.count(), 1)
        self.assertEqual(AirQualityRecord.objects.first().pm1, 10)

    def test_create_air_quality_records_bad_request(self):
        response = self.client.post(reverse('api-air-quality-data-add'), 
                                    data=self.invalid_payload, 
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
