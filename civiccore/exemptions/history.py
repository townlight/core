# SPDX-License-Identifier: AGPL-3.0-only
"""Immutable, cited jurisdiction-rule version history.

A *rule version* is one reviewed, cited statement of a jurisdictional rule at one
version number. Versions are append-only and keyed by ``(rule_id, version)`` so a
prior citation, definition and provenance can always be retrieved exactly, long
after a consumer has moved to a newer version.

Scope and non-claims
--------------------
This module persists *what a caller supplied, attributed and cited*. It never
asserts that a rule is legally correct, current, or that a jurisdiction's rules
are complete. ``coverage_declaration`` is restricted to ``synthetic-fixture`` and
``tenant-supplied`` precisely so Core cannot store a record that claims official
legal coverage. Built-in PII patterns remain non-legal suggestions.

Relationship to the evaluator
-----------------------------
There is exactly one rule evaluation path: :func:`civiccore.exemptions.evaluate`.
This module adds version history *around* it; :meth:`RuleVersion.as_rule` returns
the existing frozen :class:`civiccore.exemptions.Rule` so persisted history feeds
that evaluator instead of a second, competing rule engine. Pattern admission at
write time reuses :func:`civiccore.exemptions.validate_rule_pattern`, which runs
the same shared scanner, so an invalid or catastrophic expression is refused
before it can be stored as "reviewed".

Consumer-owned rows
-------------------
``exemption_rules`` remains the consumer's mutable working table (owned by
Records). This history is deliberately *not* a foreign key to it: the working row
may be edited or disabled, while the cited version that a scan or disclosure
review relied on must stay retrievable and unchanged. Callers pass the same
logical ``rule_id`` UUID they use for the working row.

The application owns authorization, the transaction (commit/rollback), citation
accuracy and reviewer identity. PostgreSQL enforces append-only behaviour with a
trigger; the library also refuses out-of-order, stale and conflicting writes so a
caller gets an explicit error instead of a silent overwrite.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from . import Rule, validate_rule_pattern

__all__ = [
    "RuleHistoryError",
    "JurisdictionConflictError",
    "StaleRuleVersionError",
    "RuleVersionConflictError",
    "RuleVersionInput",
    "RuleVersion",
    "RecordOutcome",
    "record_rule_version",
    "rule_version",
    "current_rule_version",
    "rule_history",
    "current_rules",
    "TABLE",
]

TABLE = "civiccore_rule_versions"

COVERAGE_DECLARATIONS = ("synthetic-fixture", "tenant-supplied")


class RuleHistoryError(ValueError):
    """Base class: the write was refused and no row was changed."""


class JurisdictionConflictError(RuleHistoryError):
    """A rule id is already bound to a different jurisdiction."""


class StaleRuleVersionError(RuleHistoryError):
    """The submitted version is not the next admissible version."""


class RuleVersionConflictError(RuleHistoryError):
    """A different definition/citation was submitted for an existing version."""


class RuleVersionInput(BaseModel):
    """One cited rule version as supplied by an authorized caller."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    rule_id: UUID
    state_code: str = Field(min_length=2, max_length=2)
    version: int = Field(ge=1)
    category: str = Field(min_length=1, max_length=100)
    # Restricted to the two rule types the shared evaluator can actually run.
    rule_type: Literal["regex", "keyword"]
    rule_definition: str = Field(min_length=1, max_length=8000)
    citation_text: str = Field(min_length=1, max_length=1000)
    citation_url: str | None = Field(default=None, max_length=2000)
    effective_from: date | None = None
    retrieved_at: AwareDatetime
    coverage_declaration: Literal["synthetic-fixture", "tenant-supplied"]

    @field_validator("state_code")
    @classmethod
    def _state_code_upper(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise ValueError("A two-letter jurisdiction code is required")
        return value

    @field_validator("citation_url")
    @classmethod
    def _citation_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if any(ch.isspace() for ch in value) or not value.startswith(("https://", "http://")):
            raise ValueError("Citation URL must be an absolute http(s) locator")
        return value

    @field_validator("rule_definition")
    @classmethod
    def _admissible_definition(cls, value: str, info) -> str:
        rule_type = info.data.get("rule_type")
        if rule_type == "regex":
            # Reuse the single shared scanner: unknown or runaway patterns never
            # enter the history as a reviewed rule.
            validate_rule_pattern(value)
        elif rule_type == "keyword" and not any(t.strip() for t in value.split(",")):
            raise ValueError("Keyword rules require at least one keyword")
        return value

    def fingerprint(self) -> str:
        """Deterministic digest of the cited content, excluding who recorded it."""
        payload = self.model_dump(mode="json")
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True)
class RuleVersion:
    """A persisted, immutable cited rule version."""

    rule_id: UUID
    state_code: str
    version: int
    category: str
    rule_type: str
    rule_definition: str
    citation_text: str
    citation_url: str | None
    effective_from: date | None
    retrieved_at: object
    coverage_declaration: str
    content_sha256: str
    recorded_by: str

    def as_rule(self) -> Rule:
        """Return the shared evaluator's rule for exactly this persisted version."""
        return Rule(
            id=self.rule_id,
            state_code=self.state_code,
            category=self.category,
            rule_type=self.rule_type,
            definition=self.rule_definition,
            version=self.version,
        )


@dataclass(frozen=True)
class RecordOutcome:
    rule_version: RuleVersion
    inserted: bool
    fingerprint: str


def _row_to_version(row) -> RuleVersion:
    return RuleVersion(
        rule_id=row["rule_id"],
        state_code=row["state_code"],
        version=row["version"],
        category=row["category"],
        rule_type=row["rule_type"],
        rule_definition=row["rule_definition"],
        citation_text=row["citation_text"],
        citation_url=row["citation_url"],
        effective_from=row["effective_from"],
        retrieved_at=row["retrieved_at"],
        coverage_declaration=row["coverage_declaration"],
        content_sha256=row["content_sha256"],
        recorded_by=row["recorded_by"],
    )


_COLUMNS = (
    "rule_id,state_code,version,category,rule_type,rule_definition,citation_text,"
    "citation_url,effective_from,retrieved_at,coverage_declaration,content_sha256,recorded_by"
)


async def _state_codes_for(session: AsyncSession, rule_id: UUID) -> set[str]:
    rows = await session.execute(
        text(f"SELECT DISTINCT state_code FROM {TABLE} WHERE rule_id=:rule_id"),
        {"rule_id": rule_id},
    )
    return {row[0] for row in rows}


async def _current_version_row(session: AsyncSession, rule_id: UUID, state_code: str):
    result = await session.execute(
        text(
            f"SELECT {_COLUMNS} FROM {TABLE} "
            "WHERE rule_id=:rule_id AND state_code=:state_code "
            "ORDER BY version DESC LIMIT 1"
        ),
        {"rule_id": rule_id, "state_code": state_code},
    )
    return result.mappings().first()


async def record_rule_version(
    session: AsyncSession,
    value: dict | RuleVersionInput,
    *,
    recorded_by: str,
    expected_current_version: int | None = None,
) -> RecordOutcome:
    """Append one cited rule version, or verify an exact repeat of one.

    ``expected_current_version`` is a compare-and-append guard: ``None`` skips it,
    ``0`` means "this rule has no history yet", and any other value must equal the
    currently stored maximum version. A stale guard, an out-of-sequence version or
    a changed definition/citation for an existing version raises rather than
    overwriting. The caller commits.
    """
    if not isinstance(recorded_by, str) or not recorded_by.strip() or len(recorded_by) > 128:
        raise RuleHistoryError("An attributed recorder identity is required")
    item = value if isinstance(value, RuleVersionInput) else RuleVersionInput.model_validate(value)
    if item.coverage_declaration not in COVERAGE_DECLARATIONS:
        raise RuleHistoryError("Unsupported coverage declaration")

    fingerprint = item.fingerprint()
    # Serialize per logical rule so two concurrent appends cannot both believe
    # they are writing the next version.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"civiccore.rule_versions:{item.state_code}:{item.rule_id}"},
    )

    other_states = await _state_codes_for(session, item.rule_id) - {item.state_code}
    if other_states:
        raise JurisdictionConflictError(
            "Rule id already belongs to a different jurisdiction; history is not shared"
        )

    current = await _current_version_row(session, item.rule_id, item.state_code)
    current_version = current["version"] if current else 0

    if expected_current_version is not None:
        if expected_current_version < 0:
            raise RuleHistoryError("expected_current_version cannot be negative")
        if expected_current_version != current_version:
            raise StaleRuleVersionError(
                "Rule history moved on; re-read the current version before appending"
            )

    if current and item.version == current_version:
        if current["content_sha256"] != fingerprint:
            raise RuleVersionConflictError(
                "That version already exists with a different definition or citation"
            )
        return RecordOutcome(_row_to_version(current), inserted=False, fingerprint=fingerprint)

    if item.version <= current_version:
        raise StaleRuleVersionError(
            "Versions are append-only and are never backfilled or renumbered"
        )
    if item.version != current_version + 1:
        raise StaleRuleVersionError("Submitted version is not the next version number")

    await session.execute(
        text(
            f"INSERT INTO {TABLE} (rule_id,state_code,version,category,rule_type,"
            "rule_definition,citation_text,citation_url,effective_from,retrieved_at,"
            "coverage_declaration,content_sha256,recorded_by) VALUES "
            "(:rule_id,:state_code,:version,:category,:rule_type,:rule_definition,"
            ":citation_text,:citation_url,:effective_from,:retrieved_at,"
            ":coverage_declaration,:content_sha256,:recorded_by)"
        ),
        {
            "rule_id": item.rule_id,
            "state_code": item.state_code,
            "version": item.version,
            "category": item.category,
            "rule_type": item.rule_type,
            "rule_definition": item.rule_definition,
            "citation_text": item.citation_text,
            "citation_url": item.citation_url,
            "effective_from": item.effective_from,
            "retrieved_at": item.retrieved_at,
            "coverage_declaration": item.coverage_declaration,
            "content_sha256": fingerprint,
            "recorded_by": recorded_by.strip(),
        },
    )
    stored = await _current_version_row(session, item.rule_id, item.state_code)
    return RecordOutcome(_row_to_version(stored), inserted=True, fingerprint=fingerprint)


async def rule_version(
    session: AsyncSession, rule_id: UUID, version: int, *, state_code: str
) -> RuleVersion | None:
    """Retrieve exactly one persisted version inside one jurisdiction."""
    state_code = _require_state_code(state_code)
    if version < 1:
        raise RuleHistoryError("Version must be >= 1")
    other_states = await _state_codes_for(session, rule_id) - {state_code}
    if other_states:
        raise JurisdictionConflictError("Rule id belongs to a different jurisdiction")
    result = await session.execute(
        text(
            f"SELECT {_COLUMNS} FROM {TABLE} "
            "WHERE rule_id=:rule_id AND state_code=:state_code AND version=:version"
        ),
        {"rule_id": rule_id, "state_code": state_code, "version": version},
    )
    row = result.mappings().first()
    return _row_to_version(row) if row else None


async def current_rule_version(
    session: AsyncSession, rule_id: UUID, *, state_code: str
) -> RuleVersion | None:
    """Retrieve the highest stored version for a rule inside one jurisdiction."""
    state_code = _require_state_code(state_code)
    other_states = await _state_codes_for(session, rule_id) - {state_code}
    if other_states:
        raise JurisdictionConflictError("Rule id belongs to a different jurisdiction")
    row = await _current_version_row(session, rule_id, state_code)
    return _row_to_version(row) if row else None


async def rule_history(
    session: AsyncSession, rule_id: UUID, *, state_code: str
) -> list[RuleVersion]:
    """Whole cited history for one rule, oldest first; empty when unknown."""
    state_code = _require_state_code(state_code)
    other_states = await _state_codes_for(session, rule_id) - {state_code}
    if other_states:
        raise JurisdictionConflictError("Rule id belongs to a different jurisdiction")
    result = await session.execute(
        text(
            f"SELECT {_COLUMNS} FROM {TABLE} "
            "WHERE rule_id=:rule_id AND state_code=:state_code ORDER BY version"
        ),
        {"rule_id": rule_id, "state_code": state_code},
    )
    return [_row_to_version(row) for row in result.mappings()]


async def current_rules(
    session: AsyncSession, state_code: str, *, rule_ids: list[UUID] | None = None
) -> list[Rule]:
    """Current-version rules for one jurisdiction, ready for ``evaluate``.

    Deterministically ordered by ``(category, rule_id)``. Only the latest persisted
    version of each rule is returned, so a superseded definition is never silently
    evaluated as current.
    """
    state_code = _require_state_code(state_code)
    params: dict = {"state_code": state_code}
    clause = ""
    if rule_ids is not None:
        if not rule_ids:
            return []
        if len(rule_ids) > 1000:
            raise RuleHistoryError("Rule selection exceeds the supported limit")
        clause = " AND rule_id = ANY(:rule_ids)"
        params["rule_ids"] = list(rule_ids)
    result = await session.execute(
        text(
            f"SELECT DISTINCT ON (rule_id) {_COLUMNS} FROM {TABLE} "
            "WHERE state_code=:state_code" + clause + " ORDER BY rule_id, version DESC"
        ),
        params,
    )
    versions = [_row_to_version(row) for row in result.mappings()]
    versions.sort(key=lambda v: (v.category, str(v.rule_id)))
    return [version.as_rule() for version in versions]


def _require_state_code(state_code: str) -> str:
    if not isinstance(state_code, str) or not state_code.strip():
        raise RuleHistoryError("An explicit jurisdiction is required")
    value = state_code.strip().upper()
    if len(value) != 2 or not value.isalpha():
        raise RuleHistoryError("A two-letter jurisdiction code is required")
    return value
