"""
Device/station API URLs (included under api/v1/devices/).

Names are under namespace 'devices': reverse('api:v1:devices:station-status').
"""
from django.urls import path

from api.views import CreateStationDataAPIView, CreateStationStatusAPIView

urlpatterns = [
    path("status/", CreateStationStatusAPIView.as_view(), name="station-status"),
    path("data/", CreateStationDataAPIView.as_view(), name="station-data"),
]
