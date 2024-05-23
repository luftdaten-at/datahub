from django.urls import path
from .views import DeviceListView, DeviceDetailView, DeviceUpdateView, DeviceMyView

urlpatterns = [
    path('', DeviceListView.as_view(), name='device-list'),
    path('my/', DeviceMyView.as_view(), name='devices-my'),
    path('<str:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('<str:pk>/update/', DeviceUpdateView.as_view(), name='device-update'),
]