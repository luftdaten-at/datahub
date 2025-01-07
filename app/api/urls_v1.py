from django.urls import path, include
from .views import WorkshopAirQualityDataView, AirQualityDataAddView

urlpatterns = [
    path('devices/', include(('api.urls_devices', 'devices'), namespace='devices')),
    path('workshops/<str:pk>/data/', WorkshopAirQualityDataView.as_view(), name='api-v1-workshop-air-quality-data'),
    path('workshops/data/add/', AirQualityDataAddView.as_view(), name='api-v1-air-quality-data-add'),
]