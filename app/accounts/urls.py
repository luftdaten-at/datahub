from django.urls import path, include

#from .views import SignupPageView
from accounts.views import AccountDeleteView, SettingsView, SignupPageView, DataDeleteView, UsersUpdateView, UsersListView, UserPasswordChangeView


urlpatterns = [
    path('delete/', AccountDeleteView.as_view(), name='account-delete'),
    path('settings/', SettingsView, name='settings'),
    path("signup/", SignupPageView.as_view(), name="signup"),
    path('data-delete/', DataDeleteView.as_view(), name='data-delete'),
    path('users/', UsersListView.as_view(), name='users-list'),
    path('users/edit/<int:user_id>/', UsersUpdateView.as_view(), name='users-edit'),
    path('users/edit/<int:user_id>/password/', UserPasswordChangeView.as_view(), name='users-edit-password'),
    path("", include("allauth.urls")),
]