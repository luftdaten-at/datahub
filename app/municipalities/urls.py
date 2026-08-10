from django.urls import path

from .views import (
    FavoriteMunicipalityToggleView,
    ManageMunicipalityListView,
    ManageMunicipalitySyncView,
    MunicipalitiesApiOverviewView,
    MunicipalityAdminLocationUpdateView,
    municipality_detail_view,
    municipalities_list_view,
)

urlpatterns = [
    path("", municipalities_list_view, name="municipalities-list"),
    path(
        "manage/",
        ManageMunicipalityListView.as_view(),
        name="municipalities-manage-list",
    ),
    path(
        "manage/sync/",
        ManageMunicipalitySyncView.as_view(),
        name="municipalities-manage-sync",
    ),
    path(
        "admin/overview/",
        MunicipalitiesApiOverviewView.as_view(),
        name="municipalities-admin-overview",
    ),
    path(
        "admin/update-location/",
        MunicipalityAdminLocationUpdateView.as_view(),
        name="municipalities-admin-update-location",
    ),
    path(
        "<str:pk>/favorite/",
        FavoriteMunicipalityToggleView.as_view(),
        name="municipality-favorite-toggle",
    ),
    path("<str:pk>/", municipality_detail_view, name="municipalities-detail"),
]
