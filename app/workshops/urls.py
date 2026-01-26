from django.urls import path
from .views import WorkshopListView, WorkshopDetailView, WorkshopMyView, WorkshopCreateView, WorkshopUpdateView, WorkshopDeleteView, WorkshopExportCsvView, invite_user_to_workshop, WorkshopImageUploadView, WorkshopManagementView, remove_user_from_workshop, WorkshopImportDataView

urlpatterns = [
    path('', WorkshopListView.as_view(), name='workshops-list'),
    path('create/', WorkshopCreateView.as_view(), name='workshop-create' ),
    path('my/', WorkshopMyView.as_view(), name='workshops-my'),
    path('<str:pk>/', WorkshopDetailView.as_view(), name='workshop-detail'),
    path('<str:pk>/update/', WorkshopUpdateView.as_view(), name='workshop-update'),
    path('<str:pk>/delete/', WorkshopDeleteView.as_view(), name='workshop-delete'),
    path('<str:pk>/export-csv/', WorkshopExportCsvView.as_view(), name='workshop_export_csv'),
    path('<str:workshop_id>/invite-user/', invite_user_to_workshop, name='invite-user-to-workshop'),
    path('<str:workshop_id>/image-upload/', WorkshopImageUploadView.as_view(), name='workshop-image-upload'),
    path('<str:workshop_id>/import-data/', WorkshopImportDataView.as_view(), name='workshop-import-data'),
    path('<str:pk>/management/', WorkshopManagementView.as_view(), name='workshop-management'),
    path('<str:workshop_id>/remove-user/<int:user_id>', remove_user_from_workshop, name='remove-user-from-workshop'),
]