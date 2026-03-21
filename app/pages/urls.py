from django.urls import path

from .views import (
    DocumentationPageView,
    HelpPageView,
    HomePageView,
    LuftdatenStatisticsProxyView,
)

urlpatterns = [
    path("documentation", DocumentationPageView.as_view(), name="documentation"),
    path("help", HelpPageView.as_view(), name="help"),
    path(
        "proxy/luftdaten-statistics/",
        LuftdatenStatisticsProxyView.as_view(),
        name="luftdaten_statistics_proxy",
    ),
    path("", HomePageView.as_view(), name="home"),
]