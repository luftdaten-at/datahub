"""
API v1 URL configuration.

Names are under namespace 'v1': reverse('api:v1:workshop-detail', kwargs={'pk': ...}).
"""
from django.urls import include, path

from api.views import (
    AirQualityDataAddView,
    CreateWorkshopSpotAPIView,
    DeleteWorkshopSpotAPIView,
    GetWorkshopSpotsAPIView,
    WorkshopAirQualityDataView,
    WorkshopDetailView,
)

urlpatterns = [
    # Devices (station data and status)
    path("devices/", include(("api.urls.devices", "devices"), namespace="devices")),

    # Workshops
    path("workshops/data/add/", AirQualityDataAddView.as_view(), name="workshop-data-add"),
    path("workshops/<str:pk>/", WorkshopDetailView.as_view(), name="workshop-detail"),
    path("workshops/<str:pk>/data/", WorkshopAirQualityDataView.as_view(), name="workshop-data"),

    # Workshop spots (nested under workshops concept)
    path("workshops/spot/add/", CreateWorkshopSpotAPIView.as_view(), name="workshop-spot-add"),
    path("workshops/spot/delete/", DeleteWorkshopSpotAPIView.as_view(), name="workshop-spot-delete"),
    path("workshops/<str:pk>/spot/", GetWorkshopSpotsAPIView.as_view(), name="workshop-spot-list"),
]
