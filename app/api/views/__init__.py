"""API views package. Re-exports all views for backward compatibility."""
from .devices import (
    CreateStationDataAPIView,
    CreateStationStatusAPIView,
    DeviceDetailView,
)
from .workshops import (
    AirQualityDataAddView,
    WorkshopAirQualityDataView,
    WorkshopDetailView,
)
from .workshop_spots import (
    CreateWorkshopSpotAPIView,
    DeleteWorkshopSpotAPIView,
    GetWorkshopSpotsAPIView,
)

__all__ = [
    "AirQualityDataAddView",
    "CreateStationDataAPIView",
    "CreateStationStatusAPIView",
    "CreateWorkshopSpotAPIView",
    "DeleteWorkshopSpotAPIView",
    "DeviceDetailView",
    "GetWorkshopSpotsAPIView",
    "WorkshopAirQualityDataView",
    "WorkshopDetailView",
]
