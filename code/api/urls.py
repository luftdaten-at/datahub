from django.urls import include, path
from .views import AirQualityDataAdd, DeviceDetailView, DeviceDataAdd, WorkshopDetailView, WorkshopAirQualityData
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('device/detail/<str:pk>/', DeviceDetailView.as_view(), name='api-device-detail'),
    path('device/data/add/', DeviceDataAdd.as_view(), name='api-device-data-add'),
    path('workshop/data/<str:pk>/', WorkshopAirQualityData.as_view(), name='api-workshop-air-quality-data'),
    path('workshop/data/add', AirQualityDataAdd.as_view(), name='api-air-quality-data-add'),
    path('workshop/detail/<str:pk>/', WorkshopDetailView.as_view(), name='api-workshop-detail'),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]