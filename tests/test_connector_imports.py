"""Tests for shipped local-first connector import helpers."""

from __future__ import annotations

import pytest

from townlight_core.connectors import (
    ConnectorImportError,
    ImportedAgendaItem,
    SUPPORTED_CONNECTORS,
    import_meeting_payload,
)


CONNECTOR_PAYLOADS = {
    "granicus": {
        "id": "gr-100",
        "name": "Budget Hearing",
        "start": "2026-05-05T19:00:00Z",
        "agenda": [
            {"id": "gr-item-1", "title": "Adopt budget ordinance", "department": "Finance"}
        ],
    },
    "legistar": {
        "MeetingId": "leg-200",
        "MeetingName": "Council Regular Meeting",
        "MeetingDate": "2026-05-06T18:30:00Z",
        "AgendaItems": [
            {"FileNumber": "24-001", "Title": "Approve minutes", "DepartmentName": "Clerk"}
        ],
    },
    "primegov": {
        "meeting_id": "pg-300",
        "title": "Planning Commission",
        "scheduled_start": "2026-05-07T17:00:00Z",
        "items": [
            {"item_id": "pg-item-1", "subject": "Subdivision plat", "owner": "Planning"}
        ],
    },
    "novusagenda": {
        "MeetingGuid": "na-400",
        "MeetingTitle": "Board Work Session",
        "MeetingDateTime": "2026-05-08T16:00:00Z",
        "Agenda": [
            {"Guid": "na-item-1", "Caption": "Capital plan update", "Dept": "Public Works"}
        ],
    },
}


@pytest.mark.parametrize("connector_name", sorted(CONNECTOR_PAYLOADS))
def test_import_meeting_payload_normalizes_meeting_payloads_with_source_provenance(
    connector_name: str,
) -> None:
    assert connector_name in SUPPORTED_CONNECTORS

    result = import_meeting_payload(
        connector_name=connector_name,
        payload=CONNECTOR_PAYLOADS[connector_name],
    )
    public = result.public_dict()

    assert public["connector"] == connector_name
    assert public["source_provenance"] == {
        "connector": connector_name,
        "imported_from": "local_payload",
        "external_meeting_id": public["external_meeting_id"],
    }
    assert public["title"]
    assert public["scheduled_start"].endswith("Z")
    assert len(public["agenda_items"]) == 1
    assert public["agenda_items"][0]["source_provenance"] == {
        "connector": connector_name,
        "imported_from": "local_payload",
        "external_item_id": public["agenda_items"][0]["external_item_id"],
    }


def test_import_meeting_payload_uses_fallback_defaults_for_partial_agenda_items() -> None:
    result = import_meeting_payload(
        connector_name="granicus",
        payload={
            "id": "gr-101",
            "name": "Supplemental Meeting",
            "start": "2026-05-05T20:00:00Z",
            "agenda": [{}],
        },
    )

    assert result.agenda_items == (
        ImportedAgendaItem(
            external_item_id="granicus-item-1",
            title="Untitled agenda item",
            department=None,
            connector="granicus",
        ),
    )


def test_import_meeting_payload_rejects_unsupported_connectors_with_fix_path() -> None:
    with pytest.raises(ConnectorImportError) as exc_info:
        import_meeting_payload(connector_name="unknown", payload={})

    assert exc_info.value.public_dict() == {
        "message": "Unsupported connector 'unknown'.",
        "fix": "Use one of: granicus, legistar, novusagenda, primegov.",
    }


def test_import_meeting_payload_rejects_missing_required_fields_with_fix_path() -> None:
    with pytest.raises(ConnectorImportError) as exc_info:
        import_meeting_payload(
            connector_name="legistar",
            payload={"MeetingId": "leg-200", "AgendaItems": []},
        )

    assert exc_info.value.public_dict() == {
        "message": "Legistar meeting payload is missing required field MeetingName.",
        "fix": "Export the meeting again with MeetingName included, then retry the local import.",
    }
