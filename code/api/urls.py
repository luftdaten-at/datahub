from django.urls import path
from .views import AirQualityDataAdd, WorkshopDetailView, WorkshopAirQualityData
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('workshop/data/<str:workshop_id>/', WorkshopAirQualityData.as_view(), name='api-workshop-air-quality-data'),
    path('workshop/data/add', AirQualityDataAdd.as_view(), name='api-air-quality-data-add'),
    path('workshop/detail/<str:pk>/', WorkshopDetailView.as_view(), name='api-workshop-detail'),
]