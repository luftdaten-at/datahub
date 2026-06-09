"""Build device sensor display data and keep the Sensor registry in sync."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from devices.models import Device, DeviceStatus, Measurement, Sensor
from main.enums import Dimension, SensorModel


def sync_sensor_registry_from_list(sensor_list: list[dict[str, Any]] | None) -> None:
    """Upsert Sensor rows for each entry in a DeviceStatus.sensor_list payload."""
    for entry in sensor_list or []:
        try:
            model_id = int(entry["model_id"])
        except (KeyError, TypeError, ValueError):
            continue
        name = SensorModel.get_sensor_name(model_id)
        serial = (entry.get("serial") or "").strip()
        Sensor.objects.update_or_create(name=name, serial=serial, defaults={})


def _latest_sensor_list(device: Device) -> list[dict[str, Any]] | None:
    try:
        status = device.status_list.filter(sensor_list__isnull=False).latest("time_received")
    except DeviceStatus.DoesNotExist:
        return None
    if status and status.sensor_list:
        return status.sensor_list
    return None


def _measurement_dims_by_model(device: Device) -> dict[int, list[str]]:
    dims_by_model: dict[int, list[str]] = defaultdict(list)
    if not device.last_update:
        return dims_by_model
    measurements = (
        Measurement.objects.filter(device=device, time_measured=device.last_update)
        .prefetch_related("values")
    )
    for measurement in measurements:
        for value in measurement.values.all():
            dim_name = Dimension.get_name(value.dimension)
            if dim_name not in dims_by_model[measurement.sensor_model]:
                dims_by_model[measurement.sensor_model].append(dim_name)
    return dims_by_model


def _lookup_sensor(name: str, serial: str | None) -> Sensor | None:
    return Sensor.objects.filter(name=name, serial=serial or "").first()


def device_sensor_entries(device: Device) -> list[dict[str, Any]]:
    """
    Structured sensor rows for device detail: name, model_id, serial, dimensions, sensor link.
    Prefers latest DeviceStatus.sensor_list; falls back to measurements at last_update.
    """
    measurement_dims = _measurement_dims_by_model(device)
    sensor_list = _latest_sensor_list(device)

    if sensor_list:
        entries: list[dict[str, Any]] = []
        for data in sensor_list:
            model_id = int(data["model_id"])
            name = SensorModel.get_sensor_name(model_id)
            raw_serial = (data.get("serial") or "").strip()
            serial = raw_serial or None
            dimensions = [Dimension.get_name(d) for d in (data.get("dimension_list") or [])]
            if not dimensions:
                dimensions = list(measurement_dims.get(model_id, []))
            entries.append(
                {
                    "name": name,
                    "model_id": model_id,
                    "serial": serial,
                    "dimensions": dimensions,
                    "sensor": _lookup_sensor(name, serial),
                }
            )
        return entries

    if not measurement_dims:
        return []

    entries = []
    for model_id in sorted(measurement_dims.keys()):
        name = SensorModel.get_sensor_name(model_id)
        entries.append(
            {
                "name": name,
                "model_id": model_id,
                "serial": None,
                "dimensions": measurement_dims[model_id],
                "sensor": _lookup_sensor(name, None),
            }
        )
    return entries
