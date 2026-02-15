from django.urls import path
from .views import DeviceDetailView, DeviceEditView, DeviceListView, DeviceLogsCSVView, DeviceMyView, DeviceNotesUpdateView, DeviceDataView, DeviceMeasurementsView, MeasurementDeleteView, calibrationView

urlpatterns = [
    path('', DeviceListView.as_view(), name='devices-list'),
    path('calibration/', calibrationView, name='calibration'),
    path('my/', DeviceMyView.as_view(), name='devices-my'),
    path('<str:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('<str:pk>/data/', DeviceDataView.as_view(), name='device-data'),
    path('<str:pk>/measurements/', DeviceMeasurementsView.as_view(), name='device-measurements'),
    path('<str:pk>/measurements/<int:measurement_pk>/delete/', MeasurementDeleteView.as_view(), name='measurement-delete'),
    path('<str:pk>/delete/', DeviceEditView.as_view(), name='device-delete'),
    path('<str:pk>/edit/', DeviceEditView.as_view(), name='device-edit'),
    path('<str:pk>/edit-notes/', DeviceNotesUpdateView.as_view(), name='device-edit-notes'),
    path('<str:pk>/logs.csv', DeviceLogsCSVView.as_view(), name='device-logs-csv'),
]