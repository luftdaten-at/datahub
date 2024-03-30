from django.urls import path
from .views import WorkshopListView, WorkshopDetailView, WorkshopMyView, WorkshopCreateView, WorkshopUpdateView, WorkshopDeleteView

urlpatterns = [
    path('', WorkshopListView.as_view(), name='workshops-list'),
    path('create/', WorkshopCreateView.as_view(), name='workshop-create' ),
    path('my/', WorkshopMyView.as_view(), name='workshops-my'),
    path('<str:pk>/', WorkshopDetailView.as_view(), name='workshop-detail'),
    path('<str:pk>/update/', WorkshopUpdateView.as_view(), name='workshop-update'),
    path('<str:pk>/delete/', WorkshopDeleteView.as_view(), name='workshop-delete'),
]