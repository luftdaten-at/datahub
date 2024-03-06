from django.urls import path
from .views import DeviceListView, DeviceDetailView

urlpatterns = [
    path('', DeviceListView.as_view(), name='device-list'),
    path('<str:pk>/', DeviceDetailView.as_view(), name='device-detail'),
]