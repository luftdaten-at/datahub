from django.urls import path
from .views import ArbeitsplatzView, HomePageView

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("arbeitsplatz/",ArbeitsplatzView.as_view(), name = "arbeitsplatz")
]