"""Connector-specific live-sync delta request planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


DELTA_QUERY_PARAMS = {
    "granicus": "modifiedSince",
    "legistar": "LastModifiedDate",
    "novusagenda": "modifiedSince",
    "primegov": "updated_since",
}


@dataclass(frozen=True)
class VendorDeltaRequestPlan:
    """Storage-neutral plan for a full or cursor-based vendor pull."""

    connector: str
    request_url: str
    delta_enabled: bool
    cursor_param: str | None
    cursor_value: str | None
    message: str
    fix: str

    def public_dict(self) -> dict[str, str | bool | None]:
        return {
            "connector": self.connector,
            "request_url": self.request_url,
            "delta_enabled": self.delta_enabled,
            "cursor_param": self.cursor_param,
            "cursor_value": self.cursor_value,
            "message": self.message,
            "fix": self.fix,
        }


def plan_vendor_delta_request(
    *,
    connector: str,
    source_url: str,
    changed_since: datetime | None,
) -> VendorDeltaRequestPlan:
    """Build the vendor request URL for a full or delta pull."""

    normalized_connector = connector.strip().lower()
    cursor_param = DELTA_QUERY_PARAMS.get(normalized_connector)
    if changed_since is None or cursor_param is None:
        return VendorDeltaRequestPlan(
            connector=normalized_connector,
            request_url=source_url,
            delta_enabled=False,
            cursor_param=cursor_param,
            cursor_value=None,
            message="Vendor pull will run as a full source request.",
            fix="Record a successful run cursor before enabling delta-only scheduled pulls.",
        )

    cursor_value = _format_cursor(changed_since)
    return VendorDeltaRequestPlan(
        connector=normalized_connector,
        request_url=_with_query_param(source_url, cursor_param, cursor_value),
        delta_enabled=True,
        cursor_param=cursor_param,
        cursor_value=cursor_value,
        message=f"{normalized_connector} vendor pull will request records changed since {cursor_value}.",
        fix="If the vendor returns missed records, reset the cursor and run one full reconciliation pull.",
    )


def _format_cursor(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _with_query_param(source_url: str, key: str, value: str) -> str:
    parsed = urlparse(source_url)
    query_items = [(existing_key, existing_value) for existing_key, existing_value in parse_qsl(parsed.query)]
    query_items = [(existing_key, existing_value) for existing_key, existing_value in query_items if existing_key != key]
    query_items.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(query_items)))


__all__ = [
    "DELTA_QUERY_PARAMS",
    "VendorDeltaRequestPlan",
    "plan_vendor_delta_request",
]
