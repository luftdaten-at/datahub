"""
API v1 URL configuration.

Names are under namespace 'v1': reverse('api:v1:workshop-detail', kwargs={'pk': ...}).
"""
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from api.views import (
    AirQualityDataAddView,
    CreateDeviceDataAPIView,
    CreateDeviceStatusAPIView,
    CreateWorkshopSpotAPIView,
    DeleteWorkshopSpotAPIView,
    GetWorkshopSpotsAPIView,
    WorkshopAirQualityDataView,
    WorkshopDetailView,
)

@extend_schema(exclude=True)
class SchemaView(SpectacularAPIView):
    api_version = "v1"


urlpatterns = [
    # OpenAPI schema and docs (under v1 for URL path; versioning disabled for schema gen)
    path("schema/", SchemaView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:v1:schema"), name="swagger-ui"),

    # Devices (status and data)
    path("devices/status/", CreateDeviceStatusAPIView.as_view(), name="device-status"),
    path("devices/data/", CreateDeviceDataAPIView.as_view(), name="device-data"),

    # Workshops
    path("workshops/data/add/", AirQualityDataAddView.as_view(), name="workshop-data-add"),
    path("workshops/<str:pk>/", WorkshopDetailView.as_view(), name="workshop-detail"),
    path("workshops/<str:pk>/data/", WorkshopAirQualityDataView.as_view(), name="workshop-data"),

    # Workshop spots (nested under workshops concept)
    path("workshops/spot/add/", CreateWorkshopSpotAPIView.as_view(), name="workshop-spot-add"),
    path("workshops/spot/delete/", DeleteWorkshopSpotAPIView.as_view(), name="workshop-spot-delete"),
    path("workshops/<str:pk>/spot/", GetWorkshopSpotsAPIView.as_view(), name="workshop-spot-list"),
]
