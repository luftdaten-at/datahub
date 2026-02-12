"""API views package. Re-exports all views for backward compatibility."""
from .devices import (
    CreateDeviceDataAPIView,
    CreateDeviceStatusAPIView,
    DeviceDetailView,
)
from .workshops import (
    AirQualityDataAddView,
    LegacyAirQualityDataAddView,
    LegacyWorkshopDetailView,
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
    "LegacyAirQualityDataAddView",
    "LegacyWorkshopDetailView",
    "CreateDeviceDataAPIView",
    "CreateDeviceStatusAPIView",
    "CreateWorkshopSpotAPIView",
    "DeleteWorkshopSpotAPIView",
    "DeviceDetailView",
    "GetWorkshopSpotsAPIView",
    "WorkshopAirQualityDataView",
    "WorkshopDetailView",
]
