from django.urls import path
from .views import CreateStationStatusAPIView, AirQualityDataAddView, DeviceDetailView, DeviceDataAddView, DeviceStatusView, WorkshopDetailView, WorkshopAirQualityDataView

urlpatterns = [
    path('devices/<str:pk>/', DeviceDetailView.as_view(), name='api-v1-device-detail'),
    path('devices/data/add/', DeviceDataAddView.as_view(), name='api-v1-device-data-add'),
    path('device/status/', DeviceStatusView.as_view(), name='api-v1-device-status'),
    path('workshops/<str:pk>/data/', WorkshopAirQualityDataView.as_view(), name='api-v1-workshop-air-quality-data'),
    path('workshops/data/add/', AirQualityDataAddView.as_view(), name='api-v1-air-quality-data-add'),
    path('workshops/<str:pk>/', WorkshopDetailView.as_view(), name='api-v1-workshop-detail'),
    path('status/', CreateStationStatusAPIView.as_view(), name='station-status'),
]