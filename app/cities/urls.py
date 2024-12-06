from django.urls import path
from .views import CitiesListView, CitiesDetailView

urlpatterns = [
    path('', CitiesListView, name='cities-list'),
    path('<str:pk>/', CitiesDetailView, name='cities-detail'),
]