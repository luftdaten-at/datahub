"""Tests for device status and data endpoints."""
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from api.models import MobilityMode
from devices.models import Device, DeviceLogs, DeviceStatus
from workshops.models import Workshop, Participant


class DeviceStatusEndpointTest(TestCase):
    """POST api/v1/devices/status/ - add device status logs."""

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(
            id="STATUS001",
            api_key="secret-key-123",
            firmware="1.0",
            model=1,
        )
        self.valid_payload = {
            "device": {
                "time": "2025-01-07T12:00:00Z",
                "device": self.device.id,
                "firmware": "1.0",
                "model": 1,
                "apikey": "secret-key-123",
                "battery": {"voltage": 3.7, "percentage": 80},
                "sensor_list": [{"model_id": 1, "dimension_list": [2, 3, 5]}],
            },
            "status_list": [
                {
                    "time": "2025-01-07T12:00:00Z",
                    "level": 1,
                    "message": "Test log entry",
                }
            ],
        }

    def test_device_status_missing_body_returns_400(self):
        response = self.client.post(
            reverse("api:v1:device-status"),
            data={},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_device_status_valid_returns_200(self):
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")
        self.assertTrue(DeviceLogs.objects.filter(device=self.device).exists())
        self.assertNotIn("log_level", response.data)

    def test_device_status_log_level_null_omits_log_level_in_response(self):
        self.assertIsNone(self.device.log_level)
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("log_level", response.data)

    def test_device_status_log_level_mismatch_includes_log_level(self):
        self.device.log_level = 0
        self.device.save(update_fields=["log_level"])
        payload = {
            **self.valid_payload,
            "status_list": [
                {
                    "time": "2025-01-07T11:00:00Z",
                    "level": 4,
                    "message": "older",
                },
                {
                    "time": "2025-01-07T13:00:00Z",
                    "level": 1,
                    "message": "newest by time",
                },
            ],
        }
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("log_level"), 0)

    def test_device_status_log_level_matches_omits_log_level(self):
        self.device.log_level = 1
        self.device.save(update_fields=["log_level"])
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("log_level", response.data)

    def test_device_status_wrong_api_key_returns_400(self):
        payload = {**self.valid_payload}
        payload["device"]["apikey"] = "wrong-key"
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_device_status_station_alias_returns_200(self):
        """Firmware may send top-level 'station' with device id in 'device' field."""
        payload = {
            "sensors": {},
            "station": {
                "time": "2026-05-30T19:51:42.000Z",
                "device": self.device.id,
                "firmware": "1.5.12",
                "model": 1,
                "apikey": "secret-key-123",
            },
            "status_list": [
                {
                    "time": "2026-05-30T19:51:42.000Z",
                    "level": 1,
                    "message": "Device online",
                }
            ],
        }
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(DeviceLogs.objects.filter(device=self.device, message="Device online").exists())

    def test_device_status_empty_status_list_returns_200(self):
        """Heartbeat with station block and empty status_list still succeeds."""
        logs_before = DeviceLogs.objects.filter(device=self.device).count()
        status_before = DeviceStatus.objects.filter(device=self.device).count()
        payload = {
            "sensors": {},
            "status_list": [],
            "station": {
                "time": "2026-05-30T19:51:48.000Z",
                "device": self.device.id,
                "firmware": "1.5.5",
                "location": {"lat": "47.261609", "lon": "11.3912323", "height": "12.0"},
                "apikey": "secret-key-123",
                "model": 1,
                "test_mode": False,
                "calibration_mode": False,
            },
        }
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")
        self.assertEqual(DeviceLogs.objects.filter(device=self.device).count(), logs_before)
        self.assertGreater(DeviceStatus.objects.filter(device=self.device).count(), status_before)

    def _status_payload(self, **device_overrides):
        base = {
            "time": "2025-01-07T12:00:00Z",
            "device": self.device.id,
            "firmware": "1.0",
            "model": 1,
            "apikey": "secret-key-123",
            "battery": {"voltage": 3.7, "percentage": 80},
        }
        base.update(device_overrides)
        return {"device": base, "status_list": []}

    def test_sensor_scan_info_updates_sensor_list(self):
        em_dash = "\u2014"
        payload = self._status_payload()
        payload["status_list"] = [
            {
                "time": "2025-01-07T12:00:00Z",
                "level": 1,
                "message": f"[INFO] Sensor scan: 2 connected {em_dash} 5, 26",
            }
        ]
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        st = DeviceStatus.objects.filter(device=self.device).latest("time_received")
        self.assertEqual(
            st.sensor_list,
            [
                {"model_id": 5, "dimension_list": []},
                {"model_id": 26, "dimension_list": []},
            ],
        )

    def test_sensor_scan_without_info_bracket_updates_sensor_list(self):
        payload = self._status_payload()
        payload["status_list"] = [
            {
                "time": "2025-01-07T12:05:00Z",
                "level": 1,
                "message": "Sensor scan: 2 connected - 7, 8",
            }
        ]
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        st = DeviceStatus.objects.filter(device=self.device).latest("time_received")
        self.assertEqual(
            st.sensor_list,
            [
                {"model_id": 7, "dimension_list": []},
                {"model_id": 8, "dimension_list": []},
            ],
        )

    def test_sensor_scan_non_info_level_does_not_update_sensor_list(self):
        payload = self._status_payload(
            sensor_list=[{"model_id": 1, "dimension_list": [2]}],
        )
        payload["status_list"] = [
            {
                "time": "2025-01-07T12:10:00Z",
                "level": 0,
                "message": "Sensor scan: 2 connected \u2014 99, 100",
            }
        ]
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        st = DeviceStatus.objects.filter(device=self.device).latest("time_received")
        self.assertEqual(st.sensor_list, [{"model_id": 1, "dimension_list": [2]}])

    def test_sensor_scan_unrelated_info_leaves_sensor_list_none(self):
        payload = self._status_payload()
        payload["status_list"] = [
            {
                "time": "2025-01-07T12:15:00Z",
                "level": 1,
                "message": "Device idle",
            }
        ]
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        st = DeviceStatus.objects.filter(device=self.device).latest("time_received")
        self.assertIsNone(st.sensor_list)

    def test_sensor_scan_preserves_dimension_list_when_model_id_overlap(self):
        payload = self._status_payload(
            sensor_list=[{"model_id": 5, "dimension_list": [2, 3, 5]}],
        )
        payload["status_list"] = [
            {
                "time": "2025-01-07T12:20:00Z",
                "level": 1,
                "message": "[INFO] Sensor scan: 2 connected \u2014 5, 26",
            }
        ]
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        st = DeviceStatus.objects.filter(device=self.device).latest("time_received")
        self.assertEqual(
            st.sensor_list,
            [
                {"model_id": 5, "dimension_list": [2, 3, 5]},
                {"model_id": 26, "dimension_list": []},
            ],
        )

    def test_sensor_scan_last_matching_line_wins(self):
        payload = self._status_payload()
        payload["status_list"] = [
            {
                "time": "2025-01-07T11:00:00Z",
                "level": 1,
                "message": "Sensor scan: 1 connected \u2014 1",
            },
            {
                "time": "2025-01-07T12:00:00Z",
                "level": 1,
                "message": "Sensor scan: 2 connected \u2014 5, 26",
            },
        ]
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        st = DeviceStatus.objects.filter(device=self.device).latest("time_received")
        self.assertEqual(
            st.sensor_list,
            [
                {"model_id": 5, "dimension_list": []},
                {"model_id": 26, "dimension_list": []},
            ],
        )

    def test_sensor_scan_battery_pipe_format_serial_optional(self):
        """Firmware line: Battery: … | sensors (N): … serial=…"""
        msg = (
            "[INFO] Sensor scan: Battery: none | sensors (2): "
            "5 serial=n/a; 26 serial=2EBE26EBF3E66049"
        )
        payload = self._status_payload()
        payload["status_list"] = [
            {"time": "2025-01-07T12:25:00Z", "level": 1, "message": msg},
        ]
        response = self.client.post(
            reverse("api:v1:device-status"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        st = DeviceStatus.objects.filter(device=self.device).latest("time_received")
        self.assertEqual(
            st.sensor_list,
            [
                {"model_id": 5, "dimension_list": []},
                {
                    "model_id": 26,
                    "dimension_list": [],
                    "serial": "2EBE26EBF3E66049",
                },
            ],
        )


class DeviceDataEndpointTest(TestCase):
    """POST api/v1/devices/data/ - add device measurement data (body: device, workshop, sensors)."""

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(
            id="DATA001",
            api_key="data-key-456",
            firmware="2.0",
            model=1,
        )
        self.workshop = Workshop.objects.create(
            title="Data Workshop",
            start_date="2025-01-01T00:00:00+00:00",
            end_date="2025-12-31T23:59:59+00:00",
        )
        self.participant = Participant.objects.create(
            name="8133a310-ffaf-11f0-8794-bbb756d19a96",
            workshop=self.workshop,
        )
        MobilityMode.objects.get_or_create(
            name="walking",
            defaults={"title": "Walking", "description": "On foot"},
        )
        self.valid_payload = {
            "device": {
                "time": "2025-01-07T11:23:23.439Z",
                "id": self.device.id,
                "firmware": "2.0",
                "model": 1,
                "apikey": "data-key-456",
            },
            "workshop": {
                "id": self.workshop.name,
                "participant": self.participant.name,
                "mode": "walking",
            },
            "location": {"lat": 48.1769523, "lon": 16.3654834},
            "sensors": {
                "1": {
                    "type": 1,
                    "data": {
                        "2": 5.0,
                        "3": 6.0,
                        "5": 7.0,
                        "6": 0.67,
                        "7": 20.0,
                    },
                },
            },
        }

    def test_device_data_missing_device_returns_400(self):
        response = self.client.post(
            reverse("api:v1:device-data"),
            data={"workshop": {"id": "x", "participant": "y", "mode": "walking"}, "sensors": {}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_device_data_without_workshop_returns_200(self):
        """Workshop is optional; request without workshop succeeds."""
        response = self.client.post(
            reverse("api:v1:device-data"),
            data={
                "device": {"time": "2025-01-07T11:23:23Z", "id": self.device.id, "firmware": "1", "model": 1, "apikey": self.device.api_key},
                "sensors": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_device_data_workshop_without_location_returns_400(self):
        """When workshop is provided, location is required."""
        response = self.client.post(
            reverse("api:v1:device-data"),
            data={
                "device": {"time": "2025-01-07T11:23:23Z", "id": self.device.id, "firmware": "1", "model": 1, "apikey": self.device.api_key},
                "workshop": {"id": self.workshop.name, "participant": self.participant.name, "mode": "walking"},
                "sensors": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_device_data_valid_returns_200(self):
        response = self.client.post(
            reverse("api:v1:device-data"),
            data=self.valid_payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_device_data_station_alias_returns_200(self):
        """Firmware may send top-level 'station' with device id in 'device' field."""
        response = self.client.post(
            reverse("api:v1:device-data"),
            data={
                "station": {
                    "time": "2025-01-07T11:23:23Z",
                    "device": self.device.id,
                    "firmware": "2.0",
                    "model": 1,
                    "apikey": self.device.api_key,
                },
                "sensors": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_device_data_station_with_nested_location_and_workshop(self):
        """Location nested under station satisfies workshop requirement."""
        response = self.client.post(
            reverse("api:v1:device-data"),
            data={
                "station": {
                    "time": "2025-01-07T11:23:23Z",
                    "device": self.device.id,
                    "firmware": "2.0",
                    "model": 1,
                    "apikey": self.device.api_key,
                    "location": {"lat": "48.1769523", "lon": "16.3654834"},
                },
                "workshop": {
                    "id": self.workshop.name,
                    "participant": self.participant.name,
                    "mode": "walking",
                },
                "sensors": {
                    "1": {
                        "type": 1,
                        "data": {"2": 5.0, "3": 6.0},
                    },
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_device_data_wrong_api_key_returns_400(self):
        payload = {**self.valid_payload}
        payload["device"] = {**payload["device"], "apikey": "wrong-key"}
        response = self.client.post(
            reverse("api:v1:device-data"),
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
