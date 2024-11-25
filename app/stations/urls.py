from django.urls import path
from .views import StationListView, StationDetailView

urlpatterns = [
    path('', StationListView, name='stations-list'),
    path('<str:pk>/', StationDetailView, name='station-detail'),
]