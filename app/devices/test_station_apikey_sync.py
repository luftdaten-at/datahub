"""Tests for syncing device API keys to api.luftdaten.at (POST /station/apikey)."""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from devices.luftdaten_station_apikey import StationApikeySyncError, sync_station_apikey
from devices.models import Device
from main.enums import LdProduct


@override_settings(
    LUFTDATEN_ADMIN_API_KEY='admin-bearer-token',
    API_URL='https://api.test.example/v1',
    LUFTDATEN_API_REQUEST_TIMEOUT=(3, 9),
)
class SyncStationApikeyHelperTests(TestCase):
    """Unit tests for sync_station_apikey (mocked HTTP)."""

    @patch('devices.luftdaten_station_apikey.requests.post')
    def test_post_url_json_and_authorization_header(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'status': 'success'}
        mock_post.return_value = mock_resp

        sync_station_apikey('device-abc-12345', 'newsecretkey12345')

        mock_post.assert_called_once()
        kwargs = mock_post.call_args.kwargs
        self.assertEqual(
            mock_post.call_args.args[0],
            'https://api.test.example/v1/station/apikey',
        )
        self.assertEqual(
            kwargs['json'],
            {'device': 'device-abc-12345', 'new_apikey': 'newsecretkey12345'},
        )
        self.assertEqual(
            kwargs['headers']['Authorization'],
            'Bearer admin-bearer-token',
        )
        self.assertEqual(kwargs['headers']['Content-Type'], 'application/json')
        self.assertEqual(kwargs['timeout'], (3, 9))

    @patch('devices.luftdaten_station_apikey.requests.post')
    def test_raises_when_admin_key_missing(self, mock_post):
        with override_settings(LUFTDATEN_ADMIN_API_KEY=''):
            with self.assertRaises(StationApikeySyncError) as ctx:
                sync_station_apikey('d1', 'x' * 16)
        self.assertEqual(ctx.exception.status_code, 503)
        mock_post.assert_not_called()

    @patch('devices.luftdaten_station_apikey.requests.post')
    def test_raises_on_422_with_detail(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.reason = 'Unprocessable Entity'
        mock_resp.text = '{"detail":"invalid key"}'
        mock_resp.json.return_value = {'detail': 'invalid key'}
        mock_post.return_value = mock_resp

        with self.assertRaises(StationApikeySyncError) as ctx:
            sync_station_apikey('dev', 'k' * 16)
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn('invalid key', str(ctx.exception))


@override_settings(
    LUFTDATEN_ADMIN_API_KEY='admin-bearer-token',
    API_URL='https://api.test.example/v1',
)
class DeviceApikeyUpdateViewSyncTests(TestCase):
    """Integration-style tests: form submit triggers sync then DB update or rollback."""

    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123',
        )
        self.device = Device.objects.create(
            id='123456789012345',
            model=LdProduct.AIR_STATION,
            auto_number=1,
            api_key='oldapikey12345678',
        )
        self.url = reverse('device-edit-apikey', kwargs={'pk': self.device.pk})

    @patch('devices.luftdaten_station_apikey.requests.post')
    def test_success_updates_device_api_key(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'status': 'success'}
        mock_post.return_value = mock_resp

        new_key = 'newapikey123456789'
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(self.url, {'api_key': new_key})

        self.assertEqual(response.status_code, 302)
        self.device.refresh_from_db()
        self.assertEqual(self.device.api_key, new_key)
        mock_post.assert_called_once()
        body = mock_post.call_args.kwargs['json']
        self.assertEqual(body['device'], self.device.pk)
        self.assertEqual(body['new_apikey'], new_key)

    @patch('devices.luftdaten_station_apikey.requests.post')
    def test_remote_failure_leaves_api_key_unchanged(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.reason = 'Unauthorized'
        mock_resp.text = ''
        mock_resp.json.return_value = {'detail': 'Invalid token'}
        mock_post.return_value = mock_resp

        new_key = 'differentkey123456'
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(self.url, {'api_key': new_key})

        self.assertEqual(response.status_code, 200)
        self.device.refresh_from_db()
        self.assertEqual(self.device.api_key, 'oldapikey12345678')
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('api_key', form.errors)
