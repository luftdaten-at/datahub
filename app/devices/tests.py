from django.contrib.auth import get_user_model
import json
import zipfile
from io import BytesIO

from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse, resolve
from django.utils import timezone

from devices.models import Device, DeviceLogs, DeviceStatus, Measurement
from devices.views import AirStationsOverviewView, DeviceListView, DeviceMoveMeasurementsView
from main.enums import LdProduct, Dimension
from api.models import AirQualityRecord


class DeviceListViewTests(TestCase):
    """Tests for the admin device list (/devices/)."""

    def setUp(self):
        self.url = reverse('devices-list')
        self.superuser = get_user_model().objects.create_superuser(
            username='listadmin',
            email='listadmin@test.com',
            password='testpass123',
        )

    def test_url_resolves_to_device_list_view(self):
        view = resolve('/devices/')
        self.assertEqual(view.func.__name__, DeviceListView.as_view().__name__)

    def test_latest_status_time_from_annotation(self):
        """Status update column uses annotated latest_status_time, not per-device queries."""
        device = Device.objects.create(id='123456789012345', model=1, auto_number=1)
        older = timezone.now() - timedelta(hours=2)
        newer = timezone.now() - timedelta(hours=1)
        DeviceStatus.objects.bulk_create([
            DeviceStatus(device=device, time_received=older),
            DeviceStatus(device=device, time_received=newer),
        ])

        self.client.login(username='listadmin', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        devices = list(response.context['devices'])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].latest_status_time, newer)
        self.assertContains(response, newer.strftime('%Y-%m-%d'))

    def test_short_device_ids_excluded(self):
        Device.objects.create(id='12345678901234', model=1, auto_number=1)
        Device.objects.create(id='123456789012345', model=1, auto_number=2)

        self.client.login(username='listadmin', password='testpass123')
        response = self.client.get(self.url)
        devices = list(response.context['devices'])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].id, '123456789012345')

    def test_query_count_does_not_scale_with_device_count(self):
        """List view must not issue one status query per device (N+1)."""
        self.client.login(username='listadmin', password='testpass123')

        def create_devices(count, id_offset):
            for i in range(count):
                device = Device.objects.create(
                    id=f'{id_offset + i:015d}',
                    model=1,
                    auto_number=i + 1,
                )
                for j in range(5):
                    DeviceStatus.objects.bulk_create([
                        DeviceStatus(
                            device=device,
                            time_received=timezone.now() - timedelta(minutes=j),
                        ),
                    ])

        create_devices(2, 100)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(self.url)
        queries_two_devices = len(ctx.captured_queries)

        create_devices(5, 200)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(self.url)
        queries_seven_devices = len(ctx.captured_queries)

        self.assertEqual(queries_two_devices, queries_seven_devices)


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

    def test_overview_summary_context(self):
        """Summary cards: 24h status, firmware and sensor breakdowns."""
        measured_time = timezone.now()
        with_log = Device.objects.create(
            id='111111111111111',
            model=LdProduct.AIR_STATION,
            auto_number=1,
            firmware='1.0',
            last_update=measured_time,
        )
        DeviceLogs.objects.create(
            device=with_log,
            timestamp=timezone.now(),
            level=1,
            message='online',
        )
        Measurement.objects.create(
            device=with_log,
            time_measured=measured_time,
            sensor_model=1,
        )
        Device.objects.create(
            id='222222222222222',
            model=LdProduct.AIR_STATION,
            auto_number=2,
            firmware='2.0',
        )

        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        summary = response.context['overview_summary']
        self.assertEqual(summary['total_count'], 2)
        self.assertEqual(summary['status_last_24h_count'], 1)
        firmware_dict = dict(summary['firmware_counts'])
        self.assertEqual(firmware_dict['1.0'], 1)
        self.assertEqual(firmware_dict['2.0'], 1)
        sensor_dict = dict(summary['sensor_counts'])
        self.assertEqual(sensor_dict['SEN5X'], 1)
        self.assertContains(response, 'Status (24h)')
        self.assertContains(response, 'By firmware')
        self.assertContains(response, 'By sensor')

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


class DeviceDataDownloadTests(TestCase):
    """device-data-download returns a ZIP with device metadata and CSV appendices."""

    def setUp(self):
        self.url = reverse("device-data-download", kwargs={"pk": "devdl1234567890"})
        self.superuser = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="testpass123",
        )
        self.device = Device.objects.create(
            id="devdl1234567890",
            model=LdProduct.AIR_STATION,
            auto_number=1,
        )

    def test_regular_user_forbidden(self):
        user = get_user_model().objects.create_user(
            username="u",
            email="u@test.com",
            password="x",
        )
        self.client.login(username="u", password="x")
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_superuser_gets_zip_with_expected_entries(self):
        self.client.login(username="admin", password="testpass123")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/zip")
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertIn("all_data.zip", r["Content-Disposition"])
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = set(zf.namelist())
            self.assertIn("device.json", names)
            self.assertIn("measurements.csv", names)
            self.assertIn("air_quality_records.csv", names)
            self.assertIn("device_status.csv", names)
            self.assertIn("device_logs.csv", names)
            meta = json.loads(zf.read("device.json").decode("utf-8"))
        self.assertEqual(meta["device"]["id"], "devdl1234567890")
        self.assertIn("device_name", meta["device"])
