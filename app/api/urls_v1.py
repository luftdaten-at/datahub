from django.urls import path
from .views import CreateStationStatusAPIView, AirQualityDataAddView, DeviceDetailView, WorkshopDetailView, WorkshopAirQualityDataView, CreateStationDataAPIView

urlpatterns = [
    path('devices/<str:pk>/', DeviceDetailView.as_view(), name='api-v1-device-detail'),
    path('workshops/<str:pk>/data/', WorkshopAirQualityDataView.as_view(), name='api-v1-workshop-air-quality-data'),
    path('workshops/data/add/', AirQualityDataAddView.as_view(), name='api-v1-air-quality-data-add'),
    path('workshops/<str:pk>/', WorkshopDetailView.as_view(), name='api-v1-workshop-detail'),
    path('status/', CreateStationStatusAPIView.as_view(), name='station-status'),
    path('data/', CreateStationDataAPIView.as_view(), name='station-data'),
]