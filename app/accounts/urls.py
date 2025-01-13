from django.urls import path, include

#from .views import SignupPageView
from accounts.views import AccountDeleteView, SettingsView, SignupPageView


urlpatterns = [
    path('delete/', AccountDeleteView.as_view(), name='account-delete'),
    path('settings/', SettingsView, name='settings'),
    path("signup/", SignupPageView.as_view(), name="signup"),
    path("", include("allauth.urls")),
]