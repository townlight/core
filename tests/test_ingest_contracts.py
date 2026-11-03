"""Tests for shipped ingest contracts."""

from __future__ import annotations

from townlight_core.ingest import (
    CitedSentence,
    CitationValidationError,
    DiscoveredRecord,
    FetchedDocument,
    HealthCheckResult,
    HealthStatus,
    SourceMaterial,
    validate_cited_sentences,
)


def test_connector_contracts_round_trip_basic_fields() -> None:
    discovered = DiscoveredRecord(
        source_path="/records/agenda.pdf",
        filename="agenda.pdf",
        file_type="pdf",
        file_size=1234,
        metadata={"department": "Clerk"},
    )
    fetched = FetchedDocument(
        source_path=discovered.source_path,
        filename=discovered.filename,
        file_type=discovered.file_type,
        content=b"%PDF-1.7",
        file_size=discovered.file_size,
        metadata=discovered.metadata,
    )
    health = HealthCheckResult(status=HealthStatus.HEALTHY, latency_ms=12)

    assert discovered.metadata["department"] == "Clerk"
    assert fetched.content.startswith(b"%PDF")
    assert health.status is HealthStatus.HEALTHY


def test_validate_cited_sentences_accepts_known_sources() -> None:
    error = validate_cited_sentences(
        source_materials=[
            SourceMaterial(source_id="src-1", label="Staff report", text="Budget recommendation"),
            SourceMaterial(source_id="src-2", label="Motion text", text="Motion approved"),
        ],
        sentences=[
            CitedSentence(text="Council approved the budget.", citations=("src-1", "src-2")),
        ],
    )

    assert error is None


def test_validate_cited_sentences_rejects_uncited_sentence() -> None:
    error = validate_cited_sentences(
        source_materials=[SourceMaterial(source_id="src-1", label="Staff report", text="Budget recommendation")],
        sentences=[CitedSentence(text="Council approved the budget.", citations=())],
    )

    assert error == CitationValidationError(
        message="Every material sentence must include at least one citation.",
        fix="Add source citations to each sentence before accepting the generated draft.",
    )


def test_validate_cited_sentences_rejects_unknown_source() -> None:
    error = validate_cited_sentences(
        source_materials=[SourceMaterial(source_id="src-1", label="Staff report", text="Budget recommendation")],
        sentences=[CitedSentence(text="Council approved the budget.", citations=("src-2",))],
    )

    assert error == CitationValidationError(
        message="Generated sentence cites an unknown source.",
        fix="Use one of the source_materials source_id values for each citation.",
    )
