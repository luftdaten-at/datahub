from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse, resolve
from django.utils import timezone

from devices.models import Device, DeviceLogs, DeviceStatus, Measurement
from devices.views import AirStationsOverviewView, DeviceMoveMeasurementsView
from main.enums import LdProduct, Dimension
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
        air_station.refresh_from_db()

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertContains(response, air_station.device_name)
        self.assertContains(response, 'Device online')
        self.assertContains(response, '2.0')

    def test_sensors_column_from_measurements_at_last_update(self):
        """Sensors column lists sensor names (not dimensions) from measurements at device.last_update."""
        measured_time = timezone.now()
        air_station = Device.objects.create(
            id='123456789012345',
            model=LdProduct.AIR_STATION,
            auto_number=1,
            last_update=measured_time,
        )
        Measurement.objects.create(
            device=air_station,
            time_measured=measured_time,
            sensor_model=1,
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertContains(response, 'SEN5X')

    def test_sensors_column_from_latest_status_when_no_measurements(self):
        """When no matching measurements, sensors come from latest DeviceStatus.sensor_list model_ids."""
        air_station = Device.objects.create(
            id='123456789012345',
            model=LdProduct.AIR_STATION,
            auto_number=1,
        )
        DeviceStatus.objects.create(
            device=air_station,
            time_received=timezone.now(),
            sensor_list=[
                {'model_id': 1, 'dimension_list': [Dimension.PM10_0]},
            ],
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertContains(response, 'SEN5X')

    def test_empty_overview_shows_message(self):
        """When no air stations exist, appropriate message is shown."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertContains(response, 'No air stations found')


class DeviceMoveMeasurementsTests(TestCase):
    """POST device-move-measurements: reassign Measurement and AirQualityRecord to another device."""

    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="testpass123",
        )
        self.user = get_user_model().objects.create_user(
            username="user",
            email="user@test.com",
            password="testpass123",
        )
        self.source = Device.objects.create(
            id="111111111111111",
            model=LdProduct.AIR_STATION,
            auto_number=1,
            device_name="Source Station",
        )
        self.target = Device.objects.create(
            id="222222222222222",
            model=LdProduct.AIR_STATION,
            auto_number=2,
            device_name="Target Station",
        )

    def test_url_resolves(self):
        path = reverse("device-move-measurements", kwargs={"pk": self.source.pk})
        view = resolve(path)
        self.assertEqual(view.func.__name__, DeviceMoveMeasurementsView.as_view().__name__)

    def test_regular_user_forbidden(self):
        self.client.login(username="user", password="testpass123")
        url = reverse("device-move-measurements", kwargs={"pk": self.source.pk})
        response = self.client.post(url, {"target_device": self.target.pk})
        self.assertEqual(response.status_code, 403)

    def test_moves_measurements_and_aqr(self):
        self.client.login(username="admin", password="testpass123")
        m = Measurement.objects.create(
            device=self.source,
            time_measured=timezone.now(),
            sensor_model=1,
        )
        aqr = AirQualityRecord.objects.create(
            device=self.source,
            time=timezone.now(),
        )
        url = reverse("device-move-measurements", kwargs={"pk": self.source.pk})
        response = self.client.post(url, {"target_device": self.target.pk})
        self.assertEqual(response.status_code, 302)
        m.refresh_from_db()
        aqr.refresh_from_db()
        self.assertEqual(m.device_id, self.target.pk)
        self.assertEqual(aqr.device_id, self.target.pk)
        self.assertEqual(self.source.measurements.count(), 0)
        self.assertEqual(self.target.measurements.count(), 1)

    def test_noop_when_empty(self):
        self.client.login(username="admin", password="testpass123")
        url = reverse("device-move-measurements", kwargs={"pk": self.source.pk})
        response = self.client.post(url, {"target_device": self.target.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.target.measurements.count(), 0)

    def test_rejects_missing_target(self):
        Measurement.objects.create(
            device=self.source,
            time_measured=timezone.now(),
            sensor_model=1,
        )
        self.client.login(username="admin", password="testpass123")
        url = reverse("device-move-measurements", kwargs={"pk": self.source.pk})
        response = self.client.post(url, {"target_device": ""})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.source.measurements.count(), 1)
