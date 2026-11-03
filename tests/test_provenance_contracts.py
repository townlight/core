"""Tests for source and provenance metadata contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from townlight_core.provenance import (
    CitationTarget,
    DocumentMetadata,
    ProvenanceBundle,
    SourceKind,
    SourceReference,
)


def test_source_kind_contract_covers_required_source_types() -> None:
    assert {kind.value for kind in SourceKind} == {
        "record",
        "document",
        "meeting_packet",
        "code_section",
        "zoning_parcel",
        "gis_export",
        "local_file",
        "url",
    }


def test_source_reference_serializes_to_export_manifest_shape() -> None:
    source = SourceReference(
        source_id="src-1",
        kind=SourceKind.MEETING_PACKET,
        title="April Council Meeting Packet",
        source_system="clerk",
        source_path="/packets/2026-04.pdf",
        captured_at=datetime(2026, 4, 2, 9, 30, tzinfo=UTC),
        checksum="sha256:abc123",
        retention_hint="retain-7-years",
        sensitivity_label="public",
        citation=CitationTarget(page=12, section="Consent Agenda"),
    )

    dumped = source.model_dump(mode="json")

    assert dumped["kind"] == "meeting_packet"
    assert dumped["captured_at"] == "2026-04-02T09:30:00Z"
    assert dumped["citation_locator"]["page"] == 12
    assert dumped["retention_hint"] == "retain-7-years"


def test_provenance_bundle_manifest_includes_sources_and_documents() -> None:
    parcel = SourceReference(
        source_id="parcel-42",
        kind=SourceKind.ZONING_PARCEL,
        title="Parcel 42 Zoning Record",
        source_system="gis",
        source_url="https://example.test/parcels/42",
        captured_at=datetime(2026, 4, 3, 8, 0, tzinfo=UTC),
        citation=CitationTarget(parcel_id="42", anchor="zoning"),
    )
    document = DocumentMetadata(
        document_id="doc-1",
        title="Staff Report",
        source=parcel,
        document_type="planning_report",
        created_at=datetime(2026, 4, 1, 17, 0, tzinfo=UTC),
        captured_at=datetime(2026, 4, 3, 8, 5, tzinfo=UTC),
        checksum="sha256:def456",
        sensitivity_label="internal",
    )
    bundle = ProvenanceBundle(
        bundle_id="export-1",
        generated_at=datetime(2026, 4, 3, 9, 0, tzinfo=UTC),
        sources=[parcel],
        documents=[document],
    )

    manifest = bundle.to_manifest()

    assert manifest["bundle_id"] == "export-1"
    assert manifest["generated_at"] == "2026-04-03T09:00:00Z"
    assert manifest["sources"][0]["kind"] == "zoning_parcel"
    assert manifest["documents"][0]["source"]["citation_locator"]["parcel_id"] == "42"


def test_provenance_models_reject_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SourceReference(
            source_id="src-naive",
            kind=SourceKind.URL,
            title="Naive URL",
            source_url="https://example.test",
            captured_at=datetime(2026, 4, 2, 9, 30),
        )
