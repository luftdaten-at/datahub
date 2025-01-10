from django.urls import path
from campaign.views import *

urlpatterns = [
    path('', CampaignsHomeView.as_view(), name='campaigns-home'),
    path('my/', CampaignsMyView.as_view(), name='campaigns-my'),
    path('create/', CampaignsCreateView.as_view(), name='campaigns-create' ),
    path('<str:pk>/', CampaignsDetailView.as_view(), name='campaigns-detail'),
    path('<str:pk>/update/', CampaignsUpdateView.as_view(), name='campaigns-update'),
    path('<str:pk>/delete/', CampaignsDeleteView.as_view(), name='campaigns-delete'),
    path('<str:pk>/add-user/', CampaignAddUserView.as_view(), name='campaign-add-user'),
    path('<str:pk>/participants/<int:user>/', ParticipantDetailView.as_view(), name='participants-detail'),
    path('rooms/<int:pk>/', RoomDetailView.as_view(), name='room-detail'),
    path('rooms/<int:pk>/delete/', RoomDeleteView.as_view(), name='room-delete'),
    path('rooms/<int:pk>/add-device/', RoomAddDeviceView.as_view(),name='room-add-device'),
    path('<str:campaign_pk>/rooms/create/', RoomCreateView.as_view(), name='room-create'),
    path('<str:campaign_pk>/rooms/<int:pk>/update/', RoomUpdateView.as_view(), name='room-update'),
]