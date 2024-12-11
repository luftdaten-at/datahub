from django.urls import path
from .views import CampaignsHomeView, CampaignsMyView, CampaignsCreateView, CampaignsDetailView, CampaignsUpdateView, CampaignsDeleteView, RoomDetailView, CampaignAddUserView

urlpatterns = [
    path('', CampaignsHomeView.as_view(), name='campaigns-home'),
    path('my/', CampaignsMyView.as_view(), name='campaigns-my'),
    path('create/', CampaignsCreateView.as_view(), name='campaigns-create' ),
    path('<str:pk>/', CampaignsDetailView.as_view(), name='campaigns-detail'),
    path('<str:pk>/update/', CampaignsUpdateView.as_view(), name='campaigns-update'),
    path('<str:pk>/delete/', CampaignsDeleteView.as_view(), name='campaigns-delete'),
    path('rooms/<int:pk>/', RoomDetailView.as_view(), name='room-detail'),
    path('campaigns/<int:pk>/add-user/', CampaignAddUserView.as_view(), name='add-user-to-campaign'),
]