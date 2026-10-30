# SPDX-License-Identifier: AGPL-3.0-only
"""Claim-bound acceptance of ingest and media artifacts produced by a leased job.

Trust boundary (deliberate and narrow):

* An artifact is admissible **only** for the job that produced it. The job identity
  (``task_id``, ``module_id``, ``task_type``, ``attempt_count``) and the ``claim_token``
  are copied from the *claimed envelope* the worker received, never from a request body,
  filename, environment variable or model output.
* The claim must still be current when the acceptance record is written: the write path
  calls :func:`civiccore.platform.task_queue.require_active_claim`, which locks the task
  row and refuses a cancelled, expired or superseded claim (``StaleTaskClaim``). A stale
  worker therefore cannot publish an artifact, and it cannot overwrite the new owner's
  state.
* Files are published inside an explicitly configured store root. Every path component is
  checked for absoluteness, ``..``/``.`` traversal, Windows drive/ADS separators and
  symlinks, and the resolved path must stay inside the root. Nothing follows a link out of
  the configured root.
* The recorded sha256 is computed from the bytes actually written to disk and re-verified
  before publication, so the database record and the file agree. A declared hash supplied
  by a caller is never trusted.
* Acceptance is attributed: ``recorded_by`` comes from the job's ``audit_subject_id``
  unless the caller supplies an already-authorized actor. An unattributed artifact is
  refused.

This module is an adapter, not a second job engine: it reuses the shipped
``civiccore_local_tasks`` claim/lease contract and adds exactly one append-only acceptance
table (``civiccore_job_artifacts``). It performs no transcription, OCR, transcoding,
embedding or provider call, and it claims none. A handler owns its own native subprocess
containment; this adapter only refuses to make an unowned or unverified file durable.

Publication order is: verify claim (row lock) -> insert acceptance row -> atomically
``os.replace`` the staged file into its final path -> commit. Any failure rolls the
transaction back and unlinks the staged and final file, so a durable file is always backed
by a committed acceptance row. A hard crash in the short window between ``os.replace`` and
``commit`` can leave an unreferenced file (never a row pointing at a missing file); such
files are enumerable under the store root and are not attributable to a job.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from sqlalchemy import BigInteger, DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from civiccore.db import Base
from civiccore.platform.task_queue import LocalTaskEnvelope, require_active_claim

#: Hard cap on one accepted artifact. Derivatives and documents only; a handler that needs
#: to keep a larger original must record its own storage receipt instead of using this path.
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024

#: Kinds this adapter is allowed to record. Anything else is refused rather than guessed at.
SUPPORTED_ARTIFACT_KINDS = frozenset({"text", "chunks-json", "media-metadata"})

STAGING_DIRNAME = ".staging"

REFUSAL_REASONS = frozenset(
    {
        "artifact-name-unsafe",
        "artifact-path-not-relative",
        "artifact-path-traversal",
        "artifact-path-symlinked",
        "artifact-path-outside-root",
        "artifact-too-large",
        "artifact-kind-unsupported",
        "artifact-hash-mismatch",
        "artifact-source-unbound",
        "artifact-not-running",
        "artifact-claim-missing",
        "artifact-not-attributed",
        "artifact-name-conflict",
        "artifact-store-not-configured",
    }
)


class ArtifactRefused(RuntimeError):
    """An artifact was refused before it could become durable and attributable."""

    def __init__(self, reason: str, detail: str = "") -> None:
        if reason not in REFUSAL_REASONS:
            raise ValueError(f"unknown artifact refusal reason: {reason}")
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


class JobArtifact(Base):
    """Append-only acceptance record for one artifact produced by one claimed job."""

    __tablename__ = "civiccore_job_artifacts"

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(128), index=True)
    module_id: Mapped[str] = mapped_column(String(64))
    task_type: Mapped[str] = mapped_column(String(100))
    claim_token: Mapped[str] = mapped_column(String(64))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    artifact_name: Mapped[str] = mapped_column(String(200))
    relative_path: Mapped[str] = mapped_column(String(400))
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    artifact_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    artifact_kind: Mapped[str] = mapped_column(String(40))
    source_sha256: Mapped[str] = mapped_column(String(64))
    source_label: Mapped[str] = mapped_column(String(200))
    recorded_by: Mapped[str] = mapped_column(String(128))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


@dataclass(frozen=True)
class ArtifactStore:
    """A configured artifact root. Every published path must resolve inside it."""

    root: Path

    @classmethod
    def open(cls, root: Path | str, *, create: bool = False) -> ArtifactStore:
        candidate = Path(root)
        if create:
            candidate.mkdir(parents=True, exist_ok=True)
        if not candidate.is_dir():
            raise ArtifactRefused("artifact-store-not-configured", str(candidate))
        if candidate.is_symlink():
            raise ArtifactRefused("artifact-path-symlinked", str(candidate))
        return cls(root=Path(os.path.realpath(candidate)))

    @property
    def staging(self) -> Path:
        return self.root / STAGING_DIRNAME


@dataclass(frozen=True)
class SourceBinding:
    """The synthetic or real source a derivative was computed from."""

    sha256: str
    label: str


@dataclass(frozen=True)
class ArtifactProposal:
    """Caller-supplied intent. The hash is recomputed and never taken from here."""

    name: str
    kind: str
    content: bytes
    source: SourceBinding


@dataclass(frozen=True)
class PreparedArtifact:
    """A staged, hash-verified file that is not yet published or recorded."""

    store: ArtifactStore
    staging_path: Path
    name: str
    kind: str
    sha256: str
    size: int
    source: SourceBinding


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _check_name(name: str) -> str:
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ArtifactRefused("artifact-name-unsafe", repr(name))
    if len(name) > 200:
        raise ArtifactRefused("artifact-name-unsafe", "name too long")
    if any(ch in name for ch in ("/", "\\", "\x00", ":")):
        raise ArtifactRefused("artifact-name-unsafe", name)
    if name != name.strip() or name.endswith("."):
        raise ArtifactRefused("artifact-name-unsafe", name)
    return name


def resolve_inside_root(store: ArtifactStore, relative: str | PurePosixPath) -> Path:
    """Resolve a relative artifact path inside ``store.root`` or refuse it.

    Refuses absolute paths, drive/UNC prefixes, ``.``/``..`` components, symlinked
    components and anything whose real path escapes the root.
    """

    pure = PurePosixPath(relative)
    if pure.is_absolute() or str(pure) != str(relative).replace("\\", "/"):
        raise ArtifactRefused("artifact-path-not-relative", str(relative))
    parts = tuple(pure.parts)
    if not parts:
        raise ArtifactRefused("artifact-path-not-relative", str(relative))
    if any(part in {"", ".", ".."} for part in parts):
        raise ArtifactRefused("artifact-path-traversal", str(relative))
    if any(part.endswith(":") or ":" in part for part in parts):
        raise ArtifactRefused("artifact-path-not-relative", str(relative))

    current = store.root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ArtifactRefused("artifact-path-symlinked", str(relative))
    resolved = Path(os.path.realpath(current))
    try:
        resolved.relative_to(store.root)
    except ValueError as exc:
        raise ArtifactRefused("artifact-path-outside-root", str(relative)) from exc
    return resolved


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def prepare_artifact(proposal: ArtifactProposal, store: ArtifactStore) -> PreparedArtifact:
    """Validate, stage, fsync and re-read-hash one artifact. Publishes nothing."""

    name = _check_name(proposal.name)
    if proposal.kind not in SUPPORTED_ARTIFACT_KINDS:
        raise ArtifactRefused("artifact-kind-unsupported", str(proposal.kind))
    source = proposal.source
    if not _is_sha256(source.sha256) or not source.label.strip():
        raise ArtifactRefused("artifact-source-unbound", source.label or "no source label")
    content = proposal.content
    if not isinstance(content, (bytes, bytearray)) or len(content) > MAX_ARTIFACT_BYTES:
        raise ArtifactRefused("artifact-too-large", str(len(content)))

    staging_dir = resolve_inside_root(store, STAGING_DIRNAME)
    staging_dir.mkdir(parents=True, exist_ok=True)
    staging_path = resolve_inside_root(store, f"{STAGING_DIRNAME}/{uuid.uuid4().hex}.part")
    expected = hashlib.sha256(bytes(content)).hexdigest()
    try:
        with open(staging_path, "xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        actual, size = _file_sha256(staging_path)
        if actual != expected or size != len(content):
            raise ArtifactRefused("artifact-hash-mismatch", f"{actual} != {expected}")
    except BaseException:
        staging_path.unlink(missing_ok=True)
        raise
    return PreparedArtifact(
        store=store,
        staging_path=staging_path,
        name=name,
        kind=proposal.kind,
        sha256=expected,
        size=len(content),
        source=source,
    )


def discard_prepared(prepared: PreparedArtifact) -> None:
    """Remove a staged artifact that will not be published."""

    prepared.staging_path.unlink(missing_ok=True)


def verify_artifact_file(store: ArtifactStore, record: JobArtifact) -> str:
    """Re-hash a recorded artifact on disk; refuse if it is missing or changed."""

    path = resolve_inside_root(store, record.relative_path)
    if not path.is_file():
        raise ArtifactRefused("artifact-path-outside-root", f"missing {record.relative_path}")
    actual, size = _file_sha256(path)
    if actual != record.artifact_sha256 or size != record.artifact_bytes:
        raise ArtifactRefused("artifact-hash-mismatch", record.relative_path)
    return actual


async def _existing(session: AsyncSession, task_id: str, name: str) -> JobArtifact | None:
    return await session.scalar(
        select(JobArtifact)
        .where(JobArtifact.task_id == task_id, JobArtifact.artifact_name == name)
        .execution_options(populate_existing=True)
    )


async def accept_artifact(
    session: AsyncSession,
    task: LocalTaskEnvelope,
    prepared: PreparedArtifact,
    *,
    recorded_by: str | None = None,
    now: datetime | None = None,
) -> JobArtifact:
    """Bind a prepared artifact to the current job identity and its live claim.

    Raises :class:`ArtifactRefused` for every local refusal and propagates
    ``StaleTaskClaim`` when the job no longer owns the work. In both cases the staged file
    is removed again, so a refused acceptance leaves no durable artifact.
    """

    actor = (recorded_by or task.audit_subject_id or "").strip()
    if not actor:
        discard_prepared(prepared)
        raise ArtifactRefused("artifact-not-attributed", task.task_id)
    if task.status != "running":
        discard_prepared(prepared)
        raise ArtifactRefused("artifact-not-running", task.status)
    if not task.claim_token:
        discard_prepared(prepared)
        raise ArtifactRefused("artifact-claim-missing", task.task_id)

    # The claim is verified *before* the idempotent shortcut, so a cancelled, expired or
    # superseded worker cannot read its own earlier acceptance as a success signal.
    try:
        await require_active_claim(
            session, task.task_id, claim_token=task.claim_token, now=now
        )
    except BaseException:
        discard_prepared(prepared)
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001 - cleanup must not mask the original refusal
            pass
        raise

    existing = await _existing(session, task.task_id, prepared.name)
    if existing is not None:
        discard_prepared(prepared)
        if existing.artifact_sha256 != prepared.sha256:
            raise ArtifactRefused("artifact-name-conflict", prepared.name)
        verify_artifact_file(prepared.store, existing)
        return existing

    artifact_id = uuid.uuid4().hex
    relative = f"{task.module_id}/{prepared.kind}/{artifact_id}/{prepared.name}"
    final_path = resolve_inside_root(prepared.store, relative)
    record = JobArtifact(
        artifact_id=artifact_id,
        task_id=task.task_id,
        module_id=task.module_id,
        task_type=task.task_type,
        claim_token=task.claim_token,
        attempt_count=task.attempt_count,
        artifact_name=prepared.name,
        relative_path=relative,
        artifact_sha256=prepared.sha256,
        artifact_bytes=prepared.size,
        artifact_kind=prepared.kind,
        source_sha256=prepared.source.sha256,
        source_label=prepared.source.label,
        recorded_by=actor[:128],
        recorded_at=now or datetime.now(UTC),
    )
    published = False
    try:
        session.add(record)
        await session.flush()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        actual, size = _file_sha256(prepared.staging_path)
        if actual != prepared.sha256 or size != prepared.size:
            raise ArtifactRefused("artifact-hash-mismatch", prepared.staging_path.name)
        os.replace(prepared.staging_path, final_path)
        published = True
        verify_artifact_file(prepared.store, record)
        await session.commit()
    except BaseException:
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001 - cleanup must not mask the original refusal
            pass
        prepared.staging_path.unlink(missing_ok=True)
        if published:
            final_path.unlink(missing_ok=True)
        raise
    return record


async def artifacts_for_task(session: AsyncSession, task_id: str) -> list[JobArtifact]:
    """Return the acceptance records of one job, oldest first."""

    result = await session.scalars(
        select(JobArtifact)
        .where(JobArtifact.task_id == task_id)
        .order_by(JobArtifact.recorded_at.asc(), JobArtifact.artifact_id.asc())
    )
    return list(result)


__all__ = [
    "ArtifactProposal",
    "ArtifactRefused",
    "ArtifactStore",
    "JobArtifact",
    "MAX_ARTIFACT_BYTES",
    "PreparedArtifact",
    "REFUSAL_REASONS",
    "STAGING_DIRNAME",
    "SUPPORTED_ARTIFACT_KINDS",
    "SourceBinding",
    "accept_artifact",
    "artifacts_for_task",
    "discard_prepared",
    "prepare_artifact",
    "resolve_inside_root",
    "verify_artifact_file",
]
