from django.urls import path, include

#from .views import SignupPageView
from accounts.views import SignupPageView


urlpatterns = [
    path("signup/", SignupPageView.as_view(), name="signup"),
    path("", include("allauth.urls")),
]