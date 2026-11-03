"""Shared ingestion pipeline and contracts for Townlight consumers.

This package exposes connector discovery/fetch contracts, cited-source
validation primitives, and the shared document-ingestion pipeline used by
module workflows that parse source files into sentence-aware vector chunks.
"""

from townlight_core.ingest.contracts import (
    CitedSentence,
    CitationValidationError,
    DiscoveredRecord,
    FetchedDocument,
    HealthCheckResult,
    HealthStatus,
    SourceMaterial,
    validate_cited_sentences,
)
from townlight_core.ingest.models import (
    DataSource,
    Document,
    DocumentChunk,
    IngestionStatus,
    SourceType,
)
from townlight_core.ingest.pipeline import (
    compute_file_hash,
    ingest_bytes,
    ingest_directory,
    ingest_file,
    ingest_structured_record,
    register_handler,
)

__all__ = [
    "CitedSentence",
    "CitationValidationError",
    "DataSource",
    "DiscoveredRecord",
    "Document",
    "DocumentChunk",
    "FetchedDocument",
    "HealthCheckResult",
    "HealthStatus",
    "IngestionStatus",
    "SourceMaterial",
    "SourceType",
    "compute_file_hash",
    "ingest_bytes",
    "ingest_directory",
    "ingest_file",
    "ingest_structured_record",
    "register_handler",
    "validate_cited_sentences",
]
