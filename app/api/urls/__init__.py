"""
API URL configuration.

Uses Django URL namespacing: reverse('api:schema'), reverse('api:v1:workshop-detail', ...).
"""
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from api.views import AirQualityDataAddView, WorkshopDetailView

app_name = "api"

urlpatterns = [
    # API versioning
    path("v1/", include(("api.urls.v1", "v1"), namespace="v1")),

    # OpenAPI schema and docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="swagger-ui"),

    # Root-level workshop endpoints (prefer v1 for new use)
    path("workshop/data/add/", AirQualityDataAddView.as_view(), name="workshop-data-add"),
    path("workshop/detail/<str:pk>/", WorkshopDetailView.as_view(), name="workshop-detail"),
]
