from django.urls import path
from .views import CampaignsHomeView, CampaignsMyView, CampaignsCreateView, CampaignsDetailView, CampaignsUpdateView, CampaignsDeleteView

urlpatterns = [
    path('', CampaignsHomeView.as_view(), name='campaigns-home'),
    path('my/', CampaignsMyView.as_view(), name='campaigns-my'),
    path('create/', CampaignsCreateView.as_view(), name='campaigns-create' ),
    path('<str:pk>/', CampaignsDetailView.as_view(), name='campaigns-detail'),
    path('<str:pk>/update/', CampaignsUpdateView.as_view(), name='campaigns-update'),
    path('<str:pk>/delete/', CampaignsDeleteView.as_view(), name='campaigns-delete'),
]