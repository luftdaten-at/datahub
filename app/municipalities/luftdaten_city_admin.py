import logging
from typing import Any

import requests
from django.conf import settings
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

# api.luftdaten.at /city/all uses countries.slug; POST /city/admin expects ISO 3166 alpha-2/3.
COUNTRY_SLUG_TO_ISO = {
    "osterreich": "AT",
}


class CityAdminUpdateError(Exception):
    """Raised when updating a city via api.luftdaten.at POST /city/admin fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def country_code_for_country_slug(country_slug: str) -> str:
    slug = (country_slug or "").strip().lower()
    if not slug:
        raise CityAdminUpdateError(_("Unknown country for this city (empty slug)."))
    code = COUNTRY_SLUG_TO_ISO.get(slug)
    if not code:
        raise CityAdminUpdateError(
            _("No ISO country code mapping for country slug “%(slug)s”. Add it in municipalities.luftdaten_city_admin.")
            % {"slug": slug}
        )
    return code


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


def update_city_admin(
    *,
    slug: str,
    name: str,
    tz: str,
    lat: float,
    lon: float,
    country_code: str,
) -> None:
    """
    POST {API_URL}/city/admin with Bearer admin auth (CityAdminSet schema).
    """
    admin_key = (settings.LUFTDATEN_ADMIN_API_KEY or "").strip()
    if not admin_key:
        raise CityAdminUpdateError(
            _("Luftdaten admin API key is not configured on this server."),
            status_code=503,
        )

    url = f"{settings.API_URL.rstrip('/')}/city/admin"
    headers = {
        "Authorization": f"Bearer {admin_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "slug": slug,
        "name": name,
        "tz": tz,
        "lat": lat,
        "lon": lon,
        "country_code": country_code,
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=settings.LUFTDATEN_API_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning(
            "city admin update request failed: slug=%s error=%s",
            slug,
            exc,
            exc_info=True,
        )
        raise CityAdminUpdateError(
            _("Could not reach api.luftdaten.at to update the city. Try again later."),
            status_code=None,
        ) from exc

    if resp.status_code == 200:
        return

    try:
        data = resp.json()
    except ValueError:
        data = None
    detail = _detail_from_response_body(data)
    msg = detail or resp.reason or _("City update was rejected by api.luftdaten.at.")

    log_fn = logger.error if resp.status_code >= 500 else logger.warning
    log_fn(
        "city admin update failed: slug=%s status=%s detail=%s",
        slug,
        resp.status_code,
        detail or (resp.text[:500] if resp.text else None),
    )

    raise CityAdminUpdateError(str(msg), status_code=resp.status_code)
