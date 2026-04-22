import logging
from typing import Any

import requests
from django.conf import settings
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class StationApikeySyncError(Exception):
    """Raised when syncing a device API key to api.luftdaten.at fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _detail_from_response_body(data: Any) -> str | None:
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        if isinstance(detail, list) and detail:
            first = detail[0]
            if isinstance(first, dict):
                msg = first.get("msg")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
    return None


def sync_station_apikey(device_id: str, new_apikey: str) -> None:
    """
    POST {API_URL}/station/apikey with Bearer admin auth.
    Raises StationApikeySyncError on configuration or HTTP/API errors.
    """
    admin_key = (settings.LUFTDATEN_ADMIN_API_KEY or "").strip()
    if not admin_key:
        raise StationApikeySyncError(
            _("Luftdaten admin API key is not configured on this server."),
            status_code=503,
        )

    url = f"{settings.API_URL.rstrip('/')}/station/apikey"
    headers = {
        "Authorization": f"Bearer {admin_key}",
        "Content-Type": "application/json",
    }
    payload = {"device": device_id, "new_apikey": new_apikey}

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning(
            "station apikey sync request failed: device=%s error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise StationApikeySyncError(
            _("Could not reach api.luftdaten.at to update the API key. Try again later."),
            status_code=None,
        ) from exc

    if resp.status_code == 200:
        try:
            body = resp.json()
        except ValueError:
            return
        if isinstance(body, dict) and body.get("status") not in (None, "success"):
            logger.warning(
                "station apikey sync unexpected 200 body: device=%s body=%s",
                device_id,
                body,
            )
        return

    try:
        data = resp.json()
    except ValueError:
        data = None
    detail = _detail_from_response_body(data)
    msg = detail or resp.reason or _("API key update was rejected by api.luftdaten.at.")

    log_fn = logger.error if resp.status_code >= 500 else logger.warning
    log_fn(
        "station apikey sync failed: device=%s status=%s detail=%s",
        device_id,
        resp.status_code,
        detail or resp.text[:500],
    )

    raise StationApikeySyncError(str(msg), status_code=resp.status_code)
