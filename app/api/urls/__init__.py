"""
API URL configuration.

Uses Django URL namespacing: reverse('api:schema'), reverse('api:v1:workshop-detail', ...).
Schema and docs live at /api/v1/schema/ and /api/v1/docs/ (versioned).
"""
from django.urls import include, path
from django.views.generic import RedirectView

from api.views import LegacyAirQualityDataAddView, LegacyWorkshopDetailView

app_name = "api"

urlpatterns = [
    # API versioning
    path("v1/", include(("api.urls.v1", "v1"), namespace="v1")),

    # Redirect /api/docs/ and /api/schema/ to versioned paths
    path("schema/", RedirectView.as_view(pattern_name="api:v1:schema", permanent=False)),
    path("schema", RedirectView.as_view(pattern_name="api:v1:schema", permanent=False)),
    path("docs/", RedirectView.as_view(pattern_name="api:v1:swagger-ui", permanent=False)),
    path("docs", RedirectView.as_view(pattern_name="api:v1:swagger-ui", permanent=False)),

    # Root-level workshop endpoints (legacy – use /api/v1/workshops/... instead)
    path("workshop/data/add/", LegacyAirQualityDataAddView.as_view(), name="workshop-data-add"),
    path("workshop/detail/<str:pk>/", LegacyWorkshopDetailView.as_view(), name="workshop-detail"),
]
