import re
from dataclasses import dataclass
from typing import Optional

from devices.models import Device
from main.enums import LdProduct

_AIR_AUTO_PK = re.compile(r"^\d{1,4}$")


@dataclass
class StationResolution:
    """Resolve URL pk to canonical station_id and optional Air Station display metadata."""

    canonical_id: str
    device: Optional[Device]
    is_air_station: bool
    air_display_name: Optional[str]

    @property
    def detail_url_pk(self) -> str:
        """Pk to use in station-detail and station-favorite-toggle URLs (short for air, no leading zeros)."""
        if self.is_air_station and self.device is not None and self.device.auto_number is not None:
            return str(int(self.device.auto_number))
        return self.canonical_id


def _air_friendly_name(device: Device) -> str:
    if device.auto_number is not None:
        return f"Air Station {int(device.auto_number)}"
    if device.device_name:
        return str(device.device_name)
    return "Air Station"


def resolve_station_from_pk(raw_pk: str) -> StationResolution:
    raw = str(raw_pk).strip()
    if not raw:
        return StationResolution(
            canonical_id=raw,
            device=None,
            is_air_station=False,
            air_display_name=None,
        )

    dev = Device.objects.filter(pk=raw).first()
    if dev is not None:
        is_air = dev.model == LdProduct.AIR_STATION
        return StationResolution(
            canonical_id=dev.id,
            device=dev,
            is_air_station=is_air,
            air_display_name=_air_friendly_name(dev) if is_air else None,
        )

    if _AIR_AUTO_PK.match(raw):
        n = int(raw)
        dev = (
            Device.objects.filter(model=LdProduct.AIR_STATION, auto_number=n)
            .order_by("id")
            .first()
        )
        if dev is not None:
            return StationResolution(
                canonical_id=dev.id,
                device=dev,
                is_air_station=True,
                air_display_name=_air_friendly_name(dev),
            )

    return StationResolution(
        canonical_id=raw,
        device=None,
        is_air_station=False,
        air_display_name=None,
    )


def air_station_url_pk_by_device_ids(
    station_ids: list[str],
) -> dict[str, str]:
    """
    Map full device id -> short auto_number string for public station URLs (no leading zeros).
    """
    if not station_ids:
        return {}
    sid_set = {str(s) for s in station_ids if s}
    devices = (
        Device.objects.filter(
            model=LdProduct.AIR_STATION,
            id__in=sid_set,
        )
        .exclude(auto_number__isnull=True)
        .only("id", "auto_number")
    )
    return {str(d.id): str(int(d.auto_number)) for d in devices}
