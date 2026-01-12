from django.test import TestCase, RequestFactory
from unittest.mock import patch, Mock, MagicMock
from django.core.cache import cache
from django.conf import settings

from stations.views import StationListView
from main.enums import Dimension, Order, OutputFormat


class StationListViewTests(TestCase):
    """Unit tests for StationListView"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.request = self.factory.get('/stations/')
        
        # Clear cache before each test
        cache.clear()
        
        # Sample CSV data for /station/topn endpoints
        self.sample_topn_csv = "station_id,lat,lon,value\n12345,48.2,16.3,25.5\n23456,48.3,16.4,30.2\n34567,48.4,16.5,20.1\n45678,48.5,16.6,15.8\n56789,48.6,16.7,18.9"
        
        # Sample JSON data for /station/all endpoint
        self.sample_all_json = [
            {
                "id": "12345",
                "last_active": "2025-01-12T10:00:00",
                "location": {
                    "lat": 48.2,
                    "lon": 16.3
                },
                "measurements_count": 100
            },
            {
                "id": "23456",
                "last_active": "2025-01-12T09:30:00",
                "location": {
                    "lat": 48.3,
                    "lon": 16.4
                },
                "measurements_count": 200
            },
            {
                "id": "34567",
                "last_active": "2025-01-12T08:00:00",
                "location": {
                    "lat": 48.4,
                    "lon": 16.5
                },
                "measurements_count": 150
            }
        ]
        
        # Sample statistics JSON
        self.sample_statistics_json = {
            "active_stations": {
                "last_hour": 277,
                "last_24_hours": 277,
                "last_7_days": 279,
                "last_30_days": 279
            }
        }
    
    def tearDown(self):
        """Clean up after each test"""
        cache.clear()
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    @patch('stations.views.cache.set')
    def test_station_list_view_success(self, mock_cache_set, mock_cache_get, mock_requests_get, mock_render):
        """Test successful StationListView with all data fetched"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        # Setup API responses
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = self.sample_all_json
        mock_response_all.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        # Setup requests.get to return different responses based on URL
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        
        # Mock render to capture context
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify render was called
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        request_arg, template_arg, context_arg = call_args[0]
        
        # Verify template
        self.assertEqual(template_arg, 'stations/list.html')
        
        # Check context data
        context = context_arg
        self.assertIn('dimension_data', context)
        self.assertIn('all_stations', context)
        self.assertIn('all_stations_json', context)
        self.assertIn('active_stations', context)
        
        # Verify dimension_data structure
        dimension_data = context['dimension_data']
        self.assertIn('pm1', dimension_data)
        self.assertIn('pm25', dimension_data)
        self.assertIn('pm10', dimension_data)
        
        # Verify each dimension has top_stations and lowest_stations
        for dim_key in ['pm1', 'pm25', 'pm10']:
            self.assertIn('top_stations', dimension_data[dim_key])
            self.assertIn('lowest_stations', dimension_data[dim_key])
        
        # Verify all_stations structure
        all_stations = context['all_stations']
        self.assertIsInstance(all_stations, list)
        if all_stations:
            self.assertIn('station_id', all_stations[0])
            self.assertIn('lat', all_stations[0])
            self.assertIn('lon', all_stations[0])
            self.assertIn('last_active', all_stations[0])
        
        # Verify active_stations structure
        active_stations = context['active_stations']
        self.assertIsInstance(active_stations, dict)
        if active_stations:
            self.assertIn('last_hour', active_stations)
            self.assertIn('last_24_hours', active_stations)
            self.assertIn('last_7_days', active_stations)
            self.assertIn('last_30_days', active_stations)
        
        # Verify cache was set
        mock_cache_set.assert_called_once()
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    @patch('stations.views.cache.set')
    def test_station_list_view_cache_hit(self, mock_cache_set, mock_cache_get, mock_requests_get, mock_render):
        """Test StationListView when cache hit occurs"""
        # Setup cache hit
        cached_stations = [
            {'station_id': '12345', 'lat': 48.2, 'lon': 16.3, 'last_active': '2025-01-12T10:00:00'},
            {'station_id': '23456', 'lat': 48.3, 'lon': 16.4, 'last_active': '2025-01-12T09:30:00'},
        ]
        mock_cache_get.return_value = cached_stations
        
        # Setup API responses for topn endpoints (still need to fetch these)
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        def side_effect(url, **kwargs):
            if '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify cache.get was called
        mock_cache_get.assert_called()
        
        # Verify cache.set was NOT called (cache hit)
        mock_cache_set.assert_not_called()
        
        # Verify all_stations from cache
        call_args = mock_render.call_args
        context = call_args[0][2]
        self.assertEqual(len(context['all_stations']), 2)
        self.assertEqual(context['all_stations'], cached_stations)
        
        # Verify /station/all was NOT called (cache hit)
        call_urls = [str(call) for call in mock_requests_get.call_args_list]
        self.assertFalse(any('/station/all' in str(call) for call in mock_requests_get.call_args_list))
        
        # Verify cached stations have last_active field
        self.assertIn('last_active', cached_stations[0])
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    def test_station_list_view_api_error_handling(self, mock_cache_get, mock_requests_get, mock_render):
        """Test StationListView error handling when API calls fail"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        # Setup requests.get to raise an exception
        mock_requests_get.side_effect = Exception("API Error")
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Assertions - view should still render with empty data
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        
        self.assertIsInstance(context['dimension_data'], dict)
        self.assertIsInstance(context['all_stations'], list)
        self.assertIsInstance(context['active_stations'], dict)
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    @patch('stations.views.cache.set')
    def test_station_list_view_json_parsing(self, mock_cache_set, mock_cache_get, mock_requests_get, mock_render):
        """Test JSON parsing logic for /station/all endpoint"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        # JSON with valid data
        json_data = [
            {
                "id": "12345",
                "last_active": "2025-01-12T10:00:00",
                "location": {
                    "lat": 48.21,
                    "lon": 16.37
                },
                "measurements_count": 100
            },
            {
                "id": "23456",
                "last_active": "2025-01-12T09:30:00",
                "location": {
                    "lat": 48.22,
                    "lon": 16.38
                },
                "measurements_count": 200
            },
            {
                "id": "34567",
                "last_active": "2025-01-12T08:00:00",
                "location": {
                    "lat": 48.23,
                    "lon": 16.39
                },
                "measurements_count": 150
            }
        ]
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = json_data
        mock_response_all.raise_for_status = Mock()
        
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify JSON parsing
        call_args = mock_render.call_args
        context = call_args[0][2]
        all_stations = context['all_stations']
        
        # Should parse 3 stations
        self.assertEqual(len(all_stations), 3)
        self.assertEqual(all_stations[0]['station_id'], '12345')
        self.assertEqual(all_stations[0]['lat'], 48.21)
        self.assertEqual(all_stations[0]['lon'], 16.37)
        self.assertEqual(all_stations[0]['last_active'], '2025-01-12T10:00:00')
        
        # Verify cache was set with parsed data
        cache_key, cached_data, timeout = mock_cache_set.call_args[0]
        self.assertEqual(cache_key, 'station_all_data')
        self.assertEqual(timeout, 3600)
        self.assertEqual(len(cached_data), 3)
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    @patch('stations.views.cache.set')
    def test_station_list_view_active_stations(self, mock_cache_set, mock_cache_get, mock_requests_get, mock_render):
        """Test active stations statistics from /statistics endpoint"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = self.sample_all_json
        mock_response_all.raise_for_status = Mock()
        
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify active stations
        call_args = mock_render.call_args
        context = call_args[0][2]
        active_stations = context['active_stations']
        
        # Should have active stations data
        self.assertIsInstance(active_stations, dict)
        self.assertEqual(active_stations['last_hour'], 277)
        self.assertEqual(active_stations['last_24_hours'], 277)
        self.assertEqual(active_stations['last_7_days'], 279)
        self.assertEqual(active_stations['last_30_days'], 279)
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    @patch('stations.views.cache.set')
    def test_station_list_view_dimension_data_structure(self, mock_cache_set, mock_cache_get, mock_requests_get, mock_render):
        """Test that dimension data has correct structure for all PM types"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = self.sample_all_json
        mock_response_all.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify dimension_data structure
        call_args = mock_render.call_args
        context = call_args[0][2]
        dimension_data = context['dimension_data']
        
        # Should have all three dimensions
        required_dimensions = ['pm1', 'pm25', 'pm10']
        for dim in required_dimensions:
            self.assertIn(dim, dimension_data)
            dim_data = dimension_data[dim]
            self.assertIn('top_stations', dim_data)
            self.assertIn('lowest_stations', dim_data)
            # Should have 5 or fewer stations (we limit to 5)
            self.assertLessEqual(len(dim_data['top_stations']), 5)
            self.assertLessEqual(len(dim_data['lowest_stations']), 5)
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    def test_station_list_view_invalid_json_data(self, mock_cache_get, mock_requests_get, mock_render):
        """Test handling of invalid JSON data"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        # JSON with invalid data (missing fields, invalid coordinates)
        invalid_json = [
            {
                "id": "12345",
                "location": {
                    "lat": "invalid",
                    "lon": 16.3
                }
            },
            {
                "id": None,
                "location": {
                    "lat": 48.2,
                    "lon": 16.4
                }
            },
            {
                "id": "34567",
                "location": {
                    "lat": 48.3,
                    "lon": 16.5
                }
            }
        ]
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = invalid_json
        mock_response_all.raise_for_status = Mock()
        
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Should handle errors gracefully
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        all_stations = context['all_stations']
        
        # Should only parse valid stations (34567)
        # Invalid stations should be skipped
        valid_stations = [s for s in all_stations if 'station_id' in s and 'lat' in s and 'lon' in s]
        self.assertLessEqual(len(valid_stations), len(all_stations))
        # Should have at least one valid station
        self.assertGreaterEqual(len(valid_stations), 1)
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    @patch('stations.views.cache.set')
    def test_station_list_view_cache_timeout(self, mock_cache_set, mock_cache_get, mock_requests_get, mock_render):
        """Test that cache is set with correct timeout"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = self.sample_all_json
        mock_response_all.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify cache.set was called with correct timeout (3600 seconds = 1 hour)
        mock_cache_set.assert_called_once()
        cache_key, cached_data, timeout = mock_cache_set.call_args[0]
        self.assertEqual(timeout, 3600)
        
        # Verify cached data includes last_active
        if cached_data:
            self.assertIn('last_active', cached_data[0])
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    @patch('stations.views.cache.set')
    def test_station_list_view_json_missing_location(self, mock_cache_set, mock_cache_get, mock_requests_get, mock_render):
        """Test JSON parsing with missing location data"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        # JSON with missing location
        json_data = [
            {
                "id": "12345",
                "last_active": "2025-01-12T10:00:00",
                "measurements_count": 100
            },
            {
                "id": "23456",
                "last_active": "2025-01-12T09:30:00",
                "location": {
                    "lat": 48.3,
                    "lon": 16.4
                },
                "measurements_count": 200
            }
        ]
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = json_data
        mock_response_all.raise_for_status = Mock()
        
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify only station with location is parsed
        call_args = mock_render.call_args
        context = call_args[0][2]
        all_stations = context['all_stations']
        
        # Should only have one station (23456 has location)
        self.assertEqual(len(all_stations), 1)
        self.assertEqual(all_stations[0]['station_id'], '23456')
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    def test_station_list_view_statistics_error(self, mock_cache_get, mock_requests_get, mock_render):
        """Test handling of statistics endpoint errors"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = self.sample_all_json
        mock_response_all.raise_for_status = Mock()
        
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        # Statistics endpoint raises error
        from requests.exceptions import RequestException
        mock_response_statistics = Mock()
        mock_response_statistics.raise_for_status.side_effect = RequestException("Statistics error")
        
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify view still renders with empty active_stations
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        
        # active_stations should be empty dict on error
        self.assertIsInstance(context['active_stations'], dict)
        self.assertEqual(len(context['active_stations']), 0)
    
    @patch('stations.views.render')
    @patch('stations.views.requests.get')
    @patch('stations.views.cache.get')
    @patch('stations.views.cache.set')
    def test_station_list_view_json_non_list_structure(self, mock_cache_set, mock_cache_get, mock_requests_get, mock_render):
        """Test handling of non-list JSON structure"""
        # Setup cache miss
        mock_cache_get.return_value = None
        
        # Non-list JSON structure
        json_data = {
            "stations": [
                {
                    "id": "12345",
                    "last_active": "2025-01-12T10:00:00",
                    "location": {
                        "lat": 48.2,
                        "lon": 16.3
                    }
                }
            ]
        }
        
        mock_response_all = Mock()
        mock_response_all.json.return_value = json_data
        mock_response_all.raise_for_status = Mock()
        
        mock_response_topn = Mock()
        mock_response_topn.text = self.sample_topn_csv
        mock_response_topn.raise_for_status = Mock()
        
        mock_response_statistics = Mock()
        mock_response_statistics.json.return_value = self.sample_statistics_json
        mock_response_statistics.raise_for_status = Mock()
        
        def side_effect(url, **kwargs):
            if '/station/all' in url:
                return mock_response_all
            elif '/station/topn' in url:
                return mock_response_topn
            elif '/statistics' in url:
                return mock_response_statistics
            return Mock()
        
        mock_requests_get.side_effect = side_effect
        mock_render.return_value = Mock(status_code=200)
        
        # Call the view
        StationListView(self.request)
        
        # Verify view handles non-list structure gracefully
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        
        # Should have empty all_stations when structure is unexpected
        self.assertIsInstance(context['all_stations'], list)
