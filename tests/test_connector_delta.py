from __future__ import annotations

from datetime import UTC, datetime

from townlight_core.connectors import plan_vendor_delta_request


def test_delta_request_plans_connector_specific_cursor_query() -> None:
    changed_since = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

    legistar = plan_vendor_delta_request(
        connector="legistar",
        source_url="https://example.test/v1/brookfield/Events?EventItems=true",
        changed_since=changed_since,
    )
    granicus = plan_vendor_delta_request(
        connector="granicus",
        source_url="https://example.test/api/meetings?existing=1",
        changed_since=changed_since,
    )

    assert legistar.delta_enabled is True
    assert legistar.cursor_param == "LastModifiedDate"
    assert "LastModifiedDate=2026-05-01T12%3A00%3A00Z" in legistar.request_url
    assert granicus.cursor_param == "modifiedSince"
    assert "existing=1" in granicus.request_url
    assert "modifiedSince=2026-05-01T12%3A00%3A00Z" in granicus.request_url


def test_delta_request_falls_back_to_full_pull_without_cursor_or_supported_connector() -> None:
    no_cursor = plan_vendor_delta_request(
        connector="primegov",
        source_url="https://example.test/api/meetings",
        changed_since=None,
    )
    unknown = plan_vendor_delta_request(
        connector="other",
        source_url="https://example.test/api/meetings",
        changed_since=datetime(2026, 5, 1, 12, 0),
    )

    assert no_cursor.delta_enabled is False
    assert no_cursor.cursor_param == "updated_since"
    assert no_cursor.request_url == "https://example.test/api/meetings"
    assert unknown.delta_enabled is False
    assert unknown.cursor_param is None
    assert unknown.fix.startswith("Record a successful run cursor")
