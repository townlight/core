"""Townlight Core hash-chained audit primitives."""

from __future__ import annotations

from .primitives import (
    AuditActor,
    AuditEvent,
    AuditHashChain,
    AuditSubject,
    PersistedAuditLogEntry,
    ZERO_HASH,
    canonical_audit_actor_id,
    canonical_audit_details,
    canonical_audit_timestamp,
    compute_persisted_audit_hash,
    record_event,
    verify_chain,
    verify_persisted_audit_chain,
)

__all__ = [
    "AuditActor",
    "AuditEvent",
    "AuditHashChain",
    "AuditSubject",
    "PersistedAuditLogEntry",
    "ZERO_HASH",
    "canonical_audit_actor_id",
    "canonical_audit_details",
    "canonical_audit_timestamp",
    "compute_persisted_audit_hash",
    "record_event",
    "verify_chain",
    "verify_persisted_audit_chain",
]
