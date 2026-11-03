"""Tests for hash-chained audit primitives."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from townlight_core.audit import (
    AuditActor,
    AuditEvent,
    AuditHashChain,
    AuditSubject,
    PersistedAuditLogEntry,
    ZERO_HASH,
    compute_persisted_audit_hash,
    record_event,
    verify_chain,
    verify_persisted_audit_chain,
)


def _actor() -> AuditActor:
    return AuditActor(actor_id="user-123", actor_type="staff", display_name="Case Worker")


def _subject() -> AuditSubject:
    return AuditSubject(subject_id="record-456", subject_type="records_request")


def test_record_event_builds_verifiable_hash_chain() -> None:
    first = record_event(
        actor=_actor(),
        action="created",
        subject=_subject(),
        source_module="records",
        timestamp=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
        metadata={"request_number": "RR-1"},
    )
    second = record_event(
        [first],
        actor=_actor(),
        action="classified",
        subject=_subject(),
        source_module="records",
        timestamp=datetime(2026, 4, 1, 12, 5, tzinfo=UTC),
        metadata={"exemption_codes": ["draft"]},
    )

    assert first.previous_hash is None
    assert second.previous_hash == first.current_hash
    assert verify_chain([first, second])


def test_verify_chain_detects_modified_payload_without_rehash() -> None:
    chain = AuditHashChain()
    event = chain.record_event(
        actor=_actor(),
        action="exported",
        subject=_subject(),
        source_module="exports",
        timestamp=datetime(2026, 4, 1, 13, 0, tzinfo=UTC),
        metadata={"format": "pdf"},
    )

    tampered = event.model_copy(update={"metadata": {"format": "docx"}})

    assert event.current_hash == chain.events[0].current_hash
    assert not verify_chain([tampered])


def test_verify_chain_detects_missing_middle_event_broken_link() -> None:
    chain = AuditHashChain()
    base_time = datetime(2026, 4, 1, 14, 0, tzinfo=UTC)
    chain.record_event(
        actor=_actor(),
        action="created",
        subject=_subject(),
        source_module="records",
        timestamp=base_time,
    )
    chain.record_event(
        actor=_actor(),
        action="reviewed",
        subject=_subject(),
        source_module="records",
        timestamp=base_time + timedelta(minutes=1),
    )
    chain.record_event(
        actor=_actor(),
        action="released",
        subject=_subject(),
        source_module="records",
        timestamp=base_time + timedelta(minutes=2),
    )

    assert chain.verify()
    assert not verify_chain([chain.events[0], chain.events[2]])


def test_verify_chain_detects_broken_previous_hash() -> None:
    chain = AuditHashChain()
    first = chain.record_event(
        actor=_actor(),
        action="created",
        subject=_subject(),
        source_module="records",
        timestamp=datetime(2026, 4, 1, 15, 0, tzinfo=UTC),
    )
    second = chain.record_event(
        actor=_actor(),
        action="updated",
        subject=_subject(),
        source_module="records",
        timestamp=datetime(2026, 4, 1, 15, 1, tzinfo=UTC),
    )
    broken = second.model_copy(update={"previous_hash": "not-the-first-hash"})

    assert first.current_hash is not None
    assert not verify_chain([first, broken])


def test_audit_event_rejects_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        AuditEvent(
            actor=_actor(),
            action="created",
            subject=_subject(),
            source_module="records",
            timestamp=datetime(2026, 4, 1, 12, 0),
        )


def test_persisted_audit_hash_matches_legacy_records_formula() -> None:
    timestamp = "2026-04-01T12:00:00+00:00"
    details = {"key": "value"}

    entry_hash = compute_persisted_audit_hash(
        previous_hash=ZERO_HASH,
        timestamp=timestamp,
        actor_id=None,
        action="test_action",
        details=details,
    )

    assert entry_hash == "292447d9d43417ec4dfd35ea8ee346d9fa43aaa4c59aa35dad492d1b22e03c4a"


def test_verify_persisted_audit_chain_accepts_archived_starting_hash() -> None:
    first_hash = compute_persisted_audit_hash(
        previous_hash="a" * 64,
        timestamp="2026-04-01T12:00:00+00:00",
        actor_id="user-1",
        action="retained",
    )
    second_hash = compute_persisted_audit_hash(
        previous_hash=first_hash,
        timestamp="2026-04-01T12:01:00+00:00",
        actor_id="user-1",
        action="reviewed",
        details={"count": 2},
    )

    entries = [
        PersistedAuditLogEntry(
            previous_hash="a" * 64,
            entry_hash=first_hash,
            timestamp="2026-04-01T12:00:00+00:00",
            actor_id="user-1",
            action="retained",
            entry_id=100,
        ),
        PersistedAuditLogEntry(
            previous_hash=first_hash,
            entry_hash=second_hash,
            timestamp="2026-04-01T12:01:00+00:00",
            actor_id="user-1",
            action="reviewed",
            details={"count": 2},
            entry_id=101,
        ),
    ]

    assert verify_persisted_audit_chain(entries) == (True, 2, "")


def test_verify_persisted_audit_chain_detects_hash_and_link_mismatch() -> None:
    first_hash = compute_persisted_audit_hash(
        previous_hash=ZERO_HASH,
        timestamp=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
        actor_id=None,
        action="created",
    )
    second_hash = compute_persisted_audit_hash(
        previous_hash=first_hash,
        timestamp=datetime(2026, 4, 1, 12, 1, tzinfo=UTC),
        actor_id=None,
        action="updated",
    )

    tampered = PersistedAuditLogEntry(
        previous_hash=ZERO_HASH,
        entry_hash=first_hash,
        timestamp=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
        actor_id=None,
        action="changed",
        entry_id=1,
    )
    broken_link = [
        PersistedAuditLogEntry(
            previous_hash=ZERO_HASH,
            entry_hash=first_hash,
            timestamp=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
            actor_id=None,
            action="created",
            entry_id=1,
        ),
        PersistedAuditLogEntry(
            previous_hash="b" * 64,
            entry_hash=second_hash,
            timestamp=datetime(2026, 4, 1, 12, 1, tzinfo=UTC),
            actor_id=None,
            action="updated",
            entry_id=2,
        ),
    ]

    assert verify_persisted_audit_chain([tampered]) == (
        False,
        0,
        "Entry 1: hash mismatch at position 0",
    )
    assert verify_persisted_audit_chain(broken_link) == (
        False,
        1,
        "Entry 2: prev_hash mismatch at position 1",
    )
