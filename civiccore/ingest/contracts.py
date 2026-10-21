"""Reusable ingest/data-source contracts for current Townlight modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNREACHABLE = "unreachable"


@dataclass
class HealthCheckResult:
    status: HealthStatus
    latency_ms: int | None = None
    error_message: str | None = None
    records_available: int | None = None
    schema_hash: str | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DiscoveredRecord:
    """A record discovered in a source system."""

    source_path: str
    filename: str
    file_type: str
    file_size: int
    last_modified: datetime | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class FetchedDocument:
    """A document fetched from a source system, ready for ingest."""

    source_path: str
    filename: str
    file_type: str
    content: bytes
    file_size: int
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SourceMaterial:
    """Human-readable source text that downstream workflows may cite."""

    source_id: str
    label: str
    text: str

    def public_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "label": self.label,
            "text": self.text,
        }


@dataclass(frozen=True)
class CitedSentence:
    """One output sentence plus the source ids it cites."""

    text: str
    citations: tuple[str, ...]

    def public_dict(self) -> dict[str, str | list[str]]:
        return {
            "text": self.text,
            "citations": list(self.citations),
        }


@dataclass(frozen=True)
class CitationValidationError:
    message: str
    fix: str


def validate_cited_sentences(
    *,
    source_materials: list[SourceMaterial],
    sentences: list[CitedSentence],
) -> CitationValidationError | None:
    """Require every sentence to cite known source ids."""

    known_sources = {source.source_id for source in source_materials}
    for sentence in sentences:
        if not sentence.citations:
            return CitationValidationError(
                message="Every material sentence must include at least one citation.",
                fix="Add source citations to each sentence before accepting the generated draft.",
            )
        unknown_sources = [citation for citation in sentence.citations if citation not in known_sources]
        if unknown_sources:
            return CitationValidationError(
                message="Generated sentence cites an unknown source.",
                fix="Use one of the source_materials source_id values for each citation.",
            )
    return None
