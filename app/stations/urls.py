from django.urls import path

from .views import (
    FavoriteStationToggleView,
    StationDetailView,
    StationListView,
)

urlpatterns = [
    path("", StationListView, name="stations-list"),
    path(
        "<str:pk>/favorite/",
        FavoriteStationToggleView.as_view(),
        name="station-favorite-toggle",
    ),
    path("<str:pk>/", StationDetailView, name="station-detail"),
]