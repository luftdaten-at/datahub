from django.urls import path

from .views import (
    DocumentationPageView,
    FAQCreateView,
    FAQEntryDetailView,
    FAQReorderView,
    GeosphereChemForecastGridProxyView,
    GeosphereChemForecastMetadataProxyView,
    HelpPageView,
    HomePageView,
)

urlpatterns = [
    path(
        "proxy/geosphere/chem-forecast/metadata/",
        GeosphereChemForecastMetadataProxyView.as_view(),
        name="geosphere-chem-forecast-metadata",
    ),
    path(
        "proxy/geosphere/chem-forecast/",
        GeosphereChemForecastGridProxyView.as_view(),
        name="geosphere-chem-forecast-grid",
    ),
    path("documentation", DocumentationPageView.as_view(), name="documentation"),
    path("help/api/faq/reorder/", FAQReorderView.as_view(), name="faq_api_reorder"),
    path("help/api/faq/", FAQCreateView.as_view(), name="faq_api_create"),
    path("help/api/faq/<int:pk>/", FAQEntryDetailView.as_view(), name="faq_api_detail"),
    path("help", HelpPageView.as_view(), name="help"),
    path("", HomePageView.as_view(), name="home"),
]
