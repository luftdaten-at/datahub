from django.urls import path
from .views import WorkshopListView, WorkshopDetailView

urlpatterns = [
    path('', WorkshopListView.as_view(), name='workshop-list'),
    path('<str:pk>/', WorkshopDetailView.as_view(), name='workshop-detail'),
]