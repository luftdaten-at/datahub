from django.urls import path
from .views import DeviceListView, DeviceDetailView, DeviceUpdateView

urlpatterns = [
    path('', DeviceListView.as_view(), name='device-list'),
    path('<str:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('<str:pk>/update/', DeviceUpdateView.as_view(), name='device-update'),
]