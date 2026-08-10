from django.urls import path

from . import views

urlpatterns = [
    path("", views.PublicSurveyListView.as_view(), name="surveys-list"),
    path("manage/", views.ManageSurveyListView.as_view(), name="surveys-manage-list"),
    path("manage/new/", views.ManageSurveyCreateView.as_view(), name="surveys-manage-create"),
    path("manage/<int:pk>/", views.ManageSurveyUpdateView.as_view(), name="surveys-manage-edit"),
    path(
        "manage/<int:pk>/questions/",
        views.ManageSurveyQuestionsView.as_view(),
        name="surveys-manage-questions",
    ),
    path(
        "manage/<int:pk>/questions/api/",
        views.ManageSurveyQuestionsAPIView.as_view(),
        name="surveys-manage-questions-api",
    ),
    path(
        "manage/<int:pk>/questions/reorder/",
        views.ManageSurveyQuestionsReorderView.as_view(),
        name="surveys-manage-questions-reorder",
    ),
    path(
        "manage/<int:pk>/questions/<int:qid>/api/",
        views.ManageSurveyQuestionAPIView.as_view(),
        name="surveys-manage-question-api",
    ),
    path(
        "manage/<int:pk>/categories/",
        views.ManageSurveyCategoriesView.as_view(),
        name="surveys-manage-categories",
    ),
    path(
        "manage/<int:pk>/responses/",
        views.ManageSurveyResponsesView.as_view(),
        name="surveys-manage-responses",
    ),
    path(
        "manage/<int:pk>/responses/export/",
        views.ManageSurveyResponsesExportView.as_view(),
        name="surveys-manage-responses-export",
    ),
    path(
        "manage/<int:pk>/publish/",
        views.ManageSurveyPublishView.as_view(),
        name="surveys-manage-publish",
    ),
    path(
        "manage/<int:pk>/close/",
        views.ManageSurveyCloseView.as_view(),
        name="surveys-manage-close",
    ),
    path(
        "manage/<int:pk>/unpublish/",
        views.ManageSurveyUnpublishView.as_view(),
        name="surveys-manage-unpublish",
    ),
    path(
        "manage/<int:pk>/reopen/",
        views.ManageSurveyReopenView.as_view(),
        name="surveys-manage-reopen",
    ),
    path("<slug:slug>/", views.PublicSurveyDetailView.as_view(), name="surveys-detail"),
    path("<slug:slug>/submit/", views.PublicSurveySubmitView.as_view(), name="surveys-submit"),
    path(
        "<slug:slug>/boundary.geojson",
        views.SurveyBoundaryGeoJSONView.as_view(),
        name="surveys-boundary-geojson",
    ),
]
