from django.urls import path, include
from .views import AirQualityDataAddView, WorkshopDetailView, WorkshopAirQualityDataView

urlpatterns = [
    path('devices/', include(('api.urls_devices', 'devices'), namespace='devices')),
    path('workshops/data/add/', AirQualityDataAddView.as_view(), name='api-v1-air-quality-data-add'),
    path('workshops/<str:pk>/', WorkshopDetailView.as_view(), name='api-v1-workshop-detail'),
    path('workshops/<str:pk>/data', WorkshopAirQualityDataView.as_view(), name='api-v1-workshop-data'),
]