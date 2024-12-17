from django.urls import path
from .views import *

urlpatterns = [
    path('', CampaignsHomeView.as_view(), name='campaigns-home'),
    path('my/', CampaignsMyView.as_view(), name='campaigns-my'),
    path('create/', CampaignsCreateView.as_view(), name='campaigns-create' ),
    path('<str:pk>/', CampaignsDetailView.as_view(), name='campaigns-detail'),
    path('<str:pk>/update/', CampaignsUpdateView.as_view(), name='campaigns-update'),
    path('<str:pk>/delete/', CampaignsDeleteView.as_view(), name='campaigns-delete'),
    path('rooms/<int:pk>/', RoomDetailView.as_view(), name='room-detail'),
    #path('campaigns/<int:pk>/add-user/', CampaignAddUserView.as_view(), name='add-user-to-campaign'),
    path('campaigns/<int:pk>/add-user/', CampaignAddUserView.as_view(), name='campaign-add-user'),
    path('rooms/<int:pk>/delete/', RoomDeleteView.as_view(), name='room-delete'),
    path('room/create/<int:campaign_pk>/', RoomCreateView.as_view(), name='room-create'),
    path('organizations/my', OrganizationsView.as_view(), name='organizations-my'),
    path('organization/create', OrganizationCreateView.as_view(), name='organization-create'),
     
]