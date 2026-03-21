from django.urls import path

from .views import (
    CitiesDetailView,
    CitiesListView,
    FavoriteCityToggleView,
)

urlpatterns = [
    path("", CitiesListView, name="cities-list"),
    path(
        "<str:pk>/favorite/",
        FavoriteCityToggleView.as_view(),
        name="city-favorite-toggle",
    ),
    path("<str:pk>/", CitiesDetailView, name="cities-detail"),
]