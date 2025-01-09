from django.urls import path
from organizations.views import *

urlpatterns = [
    path('my', OrganizationsView.as_view(), name='organizations-my'),
    path('create', OrganizationCreateView.as_view(), name='organizations-create'),
    path('<int:pk>', OrganizationDetailView.as_view(), name='organizations-detail'),
    path('<int:org_id>/remove-user/<int:user_id>', remove_user_from_organization, name='remove-user-from-organization'),
    path('<int:org_id>/invite-user', invite_user_to_organization, name='invite-user-to-organization'),
    path('<str:pk>/delete/', OrganizationDeleteView.as_view(), name='organizations-delete'),
    path('<str:pk>/update', OrganizationUpdateView.as_view(), name='organizations-update')
]