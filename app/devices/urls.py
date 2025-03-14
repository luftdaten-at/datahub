from django.urls import path
from .views import DeviceListView, DeviceDetailView, DeviceEditView, DeviceMyView, DeviceNotesUpdateView

urlpatterns = [
    path('', DeviceListView.as_view(), name='devices-list'),
    path('my/', DeviceMyView.as_view(), name='devices-my'),
    path('<str:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('<str:pk>/delete/', DeviceEditView.as_view(), name='device-delete'),
    path('<str:pk>/edit/', DeviceEditView.as_view(), name='device-edit'),
    path('<str:pk>/edit-notes/', DeviceNotesUpdateView.as_view(), name='device-edit-notes'),
]