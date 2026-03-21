from django.urls import path

from .views import (
    DocumentationPageView,
    FAQCreateView,
    FAQEntryDetailView,
    FAQReorderView,
    HelpPageView,
    HomePageView,
    LuftdatenStatisticsProxyView,
)

urlpatterns = [
    path("documentation", DocumentationPageView.as_view(), name="documentation"),
    path("help/api/faq/reorder/", FAQReorderView.as_view(), name="faq_api_reorder"),
    path("help/api/faq/", FAQCreateView.as_view(), name="faq_api_create"),
    path("help/api/faq/<int:pk>/", FAQEntryDetailView.as_view(), name="faq_api_detail"),
    path("help", HelpPageView.as_view(), name="help"),
    path(
        "proxy/luftdaten-statistics/",
        LuftdatenStatisticsProxyView.as_view(),
        name="luftdaten_statistics_proxy",
    ),
    path("", HomePageView.as_view(), name="home"),
]