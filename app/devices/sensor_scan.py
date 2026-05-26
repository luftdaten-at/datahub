"""Parse firmware Sensor scan INFO lines into DeviceStatus.sensor_list entries."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("myapp")

# Legacy: "... N connected — 1, 2, 3"
_SENSOR_SCAN_CONNECTED_RE = re.compile(
    r"(?:\[(?i:info)\]\s*)?"
    r"Sensor\s+scan:\s*(\d+)\s+connected\s*[—–-]\s*([\d,\s]+)",
    re.IGNORECASE,
)

# Extended: "... Battery: ... | sensors (N): id serial=value; ..."
_SENSOR_SCAN_BATTERY_RE = re.compile(
    r"(?:\[(?i:info)\]\s*)?"
    r"Sensor\s+scan:\s*Battery\s*:\s*(?P<battery>.+?)"
    r"\|\s*sensors\s*\(\s*(?P<count>\d+)\s*\)"
    r"\s*:\s*(?P<sensors>.+)",
    re.IGNORECASE | re.DOTALL,
)

_SENSOR_LINE_RE = re.compile(
    r"^(\d+)\s+serial\s*=\s*(.*)$",
    re.IGNORECASE,
)


_SERIAL_PLACEHOLDER = frozenset({"", "n/a", "none", "nan"})


@dataclass(frozen=True)
class SensorScanParsed:
    """Result of parsing a Sensor scan log line."""

    model_ids: list[int]
    # None = legacy comma list format (omit serial keys in sensor_list entries).
    serial_by_model: dict[int, str | None] | None


def parse_sensor_scan(message: str) -> SensorScanParsed | None:
    """
    Recognize either::

        [INFO] Sensor scan: N connected — 5, 26
        [INFO] Sensor scan: Battery: none | sensors (2): 5 serial=n/a; 26 serial=HEX…
    """
    if not message:
        return None
    text = message.strip()
    ids, serial_map = _try_parse_battery_pipe_format(text)
    if ids is not None:
        return SensorScanParsed(model_ids=ids, serial_by_model=serial_map)

    ids = _parse_connected_separator_format(text)
    if ids is not None:
        return SensorScanParsed(model_ids=ids, serial_by_model=None)
    return None


def parse_sensor_scan_model_ids(message: str) -> list[int] | None:
    """Backward-compatible helper: model IDs only, or None if no Sensor scan."""
    parsed = parse_sensor_scan(message)
    return parsed.model_ids if parsed else None


def _try_parse_battery_pipe_format(text: str) -> tuple[list[int], dict[int, str | None]] | tuple[None, None]:
    m = _SENSOR_SCAN_BATTERY_RE.search(text)
    if not m:
        return None, None
    declared = int(m.group("count"))
    raw_block = (m.group("sensors") or "").strip()

    ids: list[int] = []
    serial_by_model: dict[int, str | None] = {}
    seen: set[int] = set()

    for segment in re.split(r"\s*;\s*", raw_block):
        seg = segment.strip()
        if not seg:
            continue
        lm = _SENSOR_LINE_RE.match(seg)
        if not lm:
            logger.warning("Sensor scan: unrecognized sensor segment %r", seg)
            continue
        mid = int(lm.group(1))
        raw_serial = lm.group(2).strip() if lm.group(2) is not None else ""
        if raw_serial.lower() in _SERIAL_PLACEHOLDER:
            serial_val: str | None = None
        else:
            serial_val = raw_serial
        serial_by_model[mid] = serial_val
        if mid not in seen:
            seen.add(mid)
            ids.append(mid)

    if declared != len(ids):
        logger.warning(
            "Sensor scan declared sensors(%s) but parsed %s entries",
            declared,
            len(ids),
        )

    return ids, serial_by_model


def _parse_connected_separator_format(text: str) -> list[int] | None:
    m = _SENSOR_SCAN_CONNECTED_RE.search(text)
    if not m:
        return None
    declared_count = int(m.group(1))
    raw_ids = m.group(2)
    ids: list[int] = []
    seen: set[int] = set()
    for part in raw_ids.split(","):
        token = part.strip()
        if not token:
            continue
        mid = int(token)
        if mid not in seen:
            seen.add(mid)
            ids.append(mid)
    if declared_count != len(ids):
        logger.warning(
            "Sensor scan declared %s connected sensors but parsed %s model_ids from message",
            declared_count,
            len(ids),
        )
    return ids


def sensor_list_from_model_ids(
    model_ids: list[int],
    *,
    serial_by_model: dict[int, str | None] | None = None,
    previous: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build sensor_list payloads: one entry per unique model_id in order.

    Copies dimension_list from *previous* when the same model_id exists.
    Adds *serial* when *serial_by_model* is provided and the value is non-placeholder.
    """
    dim_by_model: dict[int, list[Any]] = {}
    if previous:
        for entry in previous:
            try:
                mid = int(entry["model_id"])
            except (KeyError, TypeError, ValueError):
                continue
            dims = entry.get("dimension_list")
            if isinstance(dims, list):
                dim_by_model[mid] = list(dims)
            else:
                dim_by_model[mid] = []

    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for mid in model_ids:
        if mid in seen:
            continue
        seen.add(mid)
        prev_dims = dim_by_model.get(mid, [])
        entry: dict[str, Any] = {"model_id": mid, "dimension_list": list(prev_dims)}
        if serial_by_model is not None and mid in serial_by_model:
            s = serial_by_model[mid]
            if s is not None and str(s).strip():
                entry["serial"] = str(s).strip()
        out.append(entry)
    return out
