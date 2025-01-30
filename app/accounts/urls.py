from django.urls import path, include

#from .views import SignupPageView
from accounts.views import AccountDeleteView, SettingsView, SignupPageView, DataDeleteView


urlpatterns = [
    path('delete/', AccountDeleteView.as_view(), name='account-delete'),
    path('settings/', SettingsView, name='settings'),
    path("signup/", SignupPageView.as_view(), name="signup"),
    path('data-delete/', DataDeleteView.as_view(), name='data-delete'),
    path("", include("allauth.urls")),
]