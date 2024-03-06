from django.urls import path
from . import views

urlpatterns = [
    path('workshop/data/add', views.air_quality_data_add, name='api-air_quality-data-add'),
    path('workshop/detail/<str:pk>/', views.workshop_detail, name='api-workshop-detail'),
]