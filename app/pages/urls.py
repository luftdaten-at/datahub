from django.urls import path
from .views import DocumentationPageView, HelpPageView, HomePageView

urlpatterns = [
    path("documentation", DocumentationPageView.as_view(), name="documentation"),
    path("help", HelpPageView.as_view(), name="help"),
    path("", HomePageView.as_view(), name="home"),
]