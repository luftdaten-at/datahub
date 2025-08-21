from django.urls import path
from .views import CustomLogViewerView, logs_json_view

app_name = 'log_viewer_custom'

urlpatterns = [
    path('', CustomLogViewerView.as_view(), name='logs'),
    path('json/', logs_json_view, name='logs_json'),
]
