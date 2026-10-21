"""Serializable source/provenance contracts.

These models describe where exported facts, records, documents, and code
references came from. They do not perform ingestion, chunking, or search.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value


class SourceKind(StrEnum):
    """Supported classes of source material."""

    RECORD = "record"
    RECORDS_DOC = "record"
    DOCUMENT = "document"
    MEETING_PACKET = "meeting_packet"
    MEETING_PACKET_FILE = "meeting_packet"
    CODE_SECTION = "code_section"
    ZONING_PARCEL = "zoning_parcel"
    GIS_EXPORT = "gis_export"
    LOCAL_FILE = "local_file"
    URL = "url"
    GENERIC_URL = "url"


class CitationTarget(BaseModel):
    """Locator that lets an export cite a precise place in a source."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    parcel_id: str | None = None
    anchor: str | None = None


class SourceReference(BaseModel):
    """Metadata for an original source used by Townlight Core."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    kind: SourceKind
    title: str
    source_system: str | None = None
    source_path: str | None = None
    source_url: str | None = None
    captured_at: datetime = Field(default_factory=_utc_now)
    checksum: str | None = None
    retention_hint: str | None = None
    sensitivity_label: str | None = None
    citation_locator: CitationTarget | None = Field(
        default=None,
        validation_alias=AliasChoices("citation_locator", "citation"),
    )

    @field_validator("captured_at")
    @classmethod
    def _captured_at_must_be_aware(cls, value: datetime) -> datetime:
        return _require_timezone(value)


class DocumentMetadata(BaseModel):
    """Document-level descriptive metadata for export manifests."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    title: str
    source: SourceReference
    document_type: str | None = None
    created_at: datetime | None = None
    captured_at: datetime = Field(default_factory=_utc_now)
    checksum: str | None = None
    retention_hint: str | None = None
    sensitivity_label: str | None = None

    @field_validator("created_at", "captured_at")
    @classmethod
    def _timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        return _require_timezone(value)


class ProvenanceBundle(BaseModel):
    """Serializable manifest of sources and documents behind an export."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    generated_at: datetime = Field(default_factory=_utc_now)
    sources: list[SourceReference] = Field(default_factory=list)
    documents: list[DocumentMetadata] = Field(default_factory=list)

    @field_validator("generated_at")
    @classmethod
    def _generated_at_must_be_aware(cls, value: datetime) -> datetime:
        return _require_timezone(value)

    def to_manifest(self) -> dict:
        """Return JSON-serializable manifest data for exports."""

        return self.model_dump(mode="json")


__all__ = [
    "CitationTarget",
    "DocumentMetadata",
    "ProvenanceBundle",
    "SourceKind",
    "SourceReference",
]
