from django.urls import path

from .views import (
    FavoriteMunicipalityToggleView,
    municipality_detail_view,
    municipalities_list_view,
)

urlpatterns = [
    path("", municipalities_list_view, name="municipalities-list"),
    path(
        "<str:pk>/favorite/",
        FavoriteMunicipalityToggleView.as_view(),
        name="municipality-favorite-toggle",
    ),
    path("<str:pk>/", municipality_detail_view, name="municipalities-detail"),
]
