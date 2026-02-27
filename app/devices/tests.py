from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse, resolve
from django.utils import timezone

from devices.models import Device, DeviceLogs, Measurement
from devices.views import AirStationsOverviewView
from main.enums import LdProduct
from api.models import AirQualityRecord


class AirStationsOverviewTests(TestCase):
    """Tests for the Air Stations overview page (admin-only)."""

    def setUp(self):
        self.url = reverse('air-stations-overview')
        self.superuser = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123',
        )
        self.regular_user = get_user_model().objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
        )

    def test_url_resolves_to_correct_view(self):
        """URL resolves to AirStationsOverviewView."""
        view = resolve('/devices/air-stations/')
        self.assertEqual(view.func.__name__, AirStationsOverviewView.as_view().__name__)

    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_regular_user_gets_403(self):
        """Non-superusers receive 403 Forbidden."""
        self.client.login(username='user', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access(self):
        """Superusers can access the overview page."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_correct_template_used(self):
        """The air_stations_overview template is used."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'devices/air_stations_overview.html')

    def test_only_air_stations_shown(self):
        """Only devices with model=AIR_STATION and id length >= 15 are shown."""
        # Valid air station (model=3, id length 15)
        air_station = Device.objects.create(
            id='123456789012345',
            model=LdProduct.AIR_STATION,
            auto_number=1,
            device_name='Air Station 0001',
            firmware='1.0',
        )
        # Wrong model - should not appear
        Device.objects.create(
            id='1234567890123456',
            model=1,  # Not AIR_STATION
            auto_number=1,
            device_name='Other Device',
        )
        # ID too short - should not appear
        Device.objects.create(
            id='12345678901234',
            model=LdProduct.AIR_STATION,
            auto_number=1,
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        air_stations = list(response.context['air_stations'])
        self.assertEqual(len(air_stations), 1)
        self.assertEqual(air_stations[0].id, air_station.id)

    def test_last_status_displayed(self):
        """Last log time and message are displayed for each device."""
        air_station = Device.objects.create(
            id='123456789012345',
            model=LdProduct.AIR_STATION,
            auto_number=1,
            device_name='Test Station',
            firmware='2.0',
        )
        DeviceLogs.objects.create(
            device=air_station,
            timestamp=timezone.now(),
            level=1,
            message='Device online',
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertContains(response, 'Test Station')
        self.assertContains(response, 'Device online')
        self.assertContains(response, '2.0')

    def test_last_send_data_from_measurement(self):
        """Last send data is computed from measurements when present."""
        air_station = Device.objects.create(
            id='123456789012345',
            model=LdProduct.AIR_STATION,
            auto_number=1,
        )
        measured_time = timezone.now()
        Measurement.objects.create(
            device=air_station,
            time_measured=measured_time,
            sensor_model=1,
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertContains(response, measured_time.strftime('%Y-%m-%d'))

    def test_last_send_data_from_air_quality_record(self):
        """Last send data is computed from air quality records when present."""
        air_station = Device.objects.create(
            id='123456789012345',
            model=LdProduct.AIR_STATION,
            auto_number=1,
        )
        aqr_time = timezone.now()
        AirQualityRecord.objects.create(
            device=air_station,
            time=aqr_time,
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertContains(response, aqr_time.strftime('%Y-%m-%d'))

    def test_empty_overview_shows_message(self):
        """When no air stations exist, appropriate message is shown."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertContains(response, 'No air stations found')
