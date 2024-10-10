from django.urls import include, path
from .views import AirQualityDataAddView, DeviceDetailView, DeviceDataAddView, WorkshopDetailView, WorkshopAirQualityDataView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('v1/', include(('api.urls_v1', 'v1'), namespace='v1')),
    # path('v2/', include(('api.urls_v2', 'v2'), namespace='v2')),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # path('device/detail/<str:pk>/', DeviceDetailView.as_view(), name='api-device-detail'),
    # path('device/data/add/', DeviceDataAddView.as_view(), name='api-device-data-add'),
    # path('workshop/data/<str:pk>/', WorkshopAirQualityDataView.as_view(), name='api-workshop-air-quality-data'),
    # path('workshop/data/add', AirQualityDataAddView.as_view(), name='api-air-quality-data-add'),
    # path('workshop/detail/<str:pk>/', WorkshopDetailView.as_view(), name='api-workshop-detail'),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]