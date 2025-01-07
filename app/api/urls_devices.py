from django.urls import path
from .views import CreateStationDataAPIView, CreateStationStatusAPIView

urlpatterns = [
    path('status/', CreateStationStatusAPIView.as_view(), name='station-status'),
    path('data/', CreateStationDataAPIView.as_view(), name='station-data'),
]
