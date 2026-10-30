# SPDX-License-Identifier: AGPL-3.0-only
"""Claim-bound artifact acceptance: identity binding, live claim, paths and hashes.

Unit tests of the refusal and binding contract. They need no database: the live-claim check
is exercised through an in-memory stand-in that mirrors ``require_active_claim`` semantics,
while the same code path against real PostgreSQL rows is asserted by
``work/beta-foundations/core-job-adapters-01/harness.py``.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import civiccore.tasks.artifacts as module
from civiccore.platform import LocalTaskEnvelope
from civiccore.platform.task_queue import StaleTaskClaim
from civiccore.tasks.artifacts import (
    MAX_ARTIFACT_BYTES,
    REFUSAL_REASONS,
    ArtifactProposal,
    ArtifactRefused,
    ArtifactStore,
    JobArtifact,
    SourceBinding,
    accept_artifact,
    artifacts_for_task,
    prepare_artifact,
    resolve_inside_root,
    verify_artifact_file,
)


SOURCE = SourceBinding(
    sha256=hashlib.sha256(b"synthetic source").hexdigest(), label="synthetic-source.txt"
)


def make_task(**overrides) -> LocalTaskEnvelope:
    values = dict(
        task_id="task-1",
        module_id="meetings",
        task_type="ingest.media.derive",
        status="running",
        payload={},
        attempt_count=0,
        queued_at=datetime.now(UTC),
        audit_subject_id="staff@example.gov",
        claim_token="a" * 32,
        lease_expires_at=datetime.now(UTC) + timedelta(seconds=300),
    )
    values.update(overrides)
    return LocalTaskEnvelope(**values)


class FakeSession:
    """In-memory stand-in for the session surface the adapter uses."""

    def __init__(self, *, stale: bool = False, rows=None) -> None:
        self.stale = stale
        self.rows: list[JobArtifact] = list(rows or [])
        self.commits = 0
        self.rollbacks = 0

    def add(self, record: JobArtifact) -> None:
        self.rows.append(record)

    async def scalars(self, statement):  # noqa: ANN001
        task_id = statement.compile().params.get("task_id_1")
        return [row for row in self.rows if row.task_id == task_id]

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.fixture()
def store(tmp_path: Path) -> ArtifactStore:
    return ArtifactStore.open(tmp_path / "artifacts", create=True)


@pytest.fixture(autouse=True)
def _fake_claim_and_lookup(monkeypatch: pytest.MonkeyPatch):
    """Replace the two session-facing calls with in-memory equivalents."""

    async def fake_require(session, task_id, *, claim_token, now=None):  # noqa: ANN001
        if session.stale:
            raise StaleTaskClaim("Job ownership expired, cancelled or changed")
        return None

    async def fake_existing(session, task_id, name):  # noqa: ANN001
        for row in session.rows:
            if row.task_id == task_id and row.artifact_name == name:
                return row
        return None

    monkeypatch.setattr(module, "require_active_claim", fake_require)
    monkeypatch.setattr(module, "_existing", fake_existing)


def proposal(
    name: str = "derived.txt",
    kind: str = "text",
    content: bytes = b"synthetic derived text.",
    source: SourceBinding = SOURCE,
) -> ArtifactProposal:
    return ArtifactProposal(name=name, kind=kind, content=content, source=source)


def published_files(store: ArtifactStore) -> list[Path]:
    return sorted(
        path
        for path in store.root.rglob("*")
        if path.is_file() and path.parent != store.staging
    )


def test_prepare_artifact_hashes_written_bytes_and_publishes_nothing(store: ArtifactStore) -> None:
    prepared = prepare_artifact(proposal(), store)

    assert prepared.sha256 == hashlib.sha256(b"synthetic derived text.").hexdigest()
    assert prepared.size == 23
    assert prepared.staging_path.is_file()
    assert prepared.staging_path.parent == store.staging
    assert published_files(store) == []


@pytest.mark.parametrize(
    "bad_name",
    ["", ".", "..", "../escape.txt", "nested/file.txt", "nested\\file.txt", "c:ads.txt", "pad."],
)
def test_unsafe_artifact_names_are_refused(store: ArtifactStore, bad_name: str) -> None:
    with pytest.raises(ArtifactRefused) as excinfo:
        prepare_artifact(proposal(name=bad_name), store)
    assert excinfo.value.reason == "artifact-name-unsafe"
    assert not list(store.root.rglob("*.part"))


def test_unsupported_kind_is_refused(store: ArtifactStore) -> None:
    with pytest.raises(ArtifactRefused) as excinfo:
        prepare_artifact(proposal(kind="transcript"), store)
    assert excinfo.value.reason == "artifact-kind-unsupported"


def test_oversized_artifact_is_refused_before_any_file(store: ArtifactStore) -> None:
    with pytest.raises(ArtifactRefused) as excinfo:
        prepare_artifact(proposal(content=b"x" * (MAX_ARTIFACT_BYTES + 1)), store)
    assert excinfo.value.reason == "artifact-too-large"
    assert not list(store.root.rglob("*.part"))


def test_unbound_source_is_refused(store: ArtifactStore) -> None:
    for source in (
        SourceBinding(sha256="nothex", label="synthetic-source.txt"),
        SourceBinding(sha256=SOURCE.sha256, label="  "),
    ):
        with pytest.raises(ArtifactRefused) as excinfo:
            prepare_artifact(proposal(source=source), store)
        assert excinfo.value.reason == "artifact-source-unbound"


@pytest.mark.parametrize(
    "relative",
    [
        "../outside.txt",
        "a/../../outside.txt",
        "/etc/passwd",
        "C:/windows/x",
        "//server/share/x",
        "a/./b.txt",
        "a//b.txt",
        "nested\\..\\x.txt",
    ],
)
def test_path_traversal_and_absolute_paths_are_refused(
    store: ArtifactStore, relative: str
) -> None:
    with pytest.raises(ArtifactRefused) as excinfo:
        resolve_inside_root(store, relative)
    assert excinfo.value.reason in {
        "artifact-path-traversal",
        "artifact-path-not-relative",
    }


def test_configured_root_refuses_a_symlinked_root(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    try:
        os.symlink(real, link, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:  # pragma: no cover - Windows privilege
        pytest.skip(f"symlink creation unavailable on this host: {exc}")
    with pytest.raises(ArtifactRefused) as excinfo:
        ArtifactStore.open(link)
    assert excinfo.value.reason == "artifact-path-symlinked"


async def test_accept_artifact_binds_task_identity_and_claim(store: ArtifactStore) -> None:
    task = make_task()
    session = FakeSession()
    prepared = prepare_artifact(proposal(), store)

    record = await accept_artifact(session, task, prepared)

    assert record.task_id == task.task_id
    assert record.module_id == task.module_id
    assert record.task_type == task.task_type
    assert record.claim_token == task.claim_token
    assert record.attempt_count == task.attempt_count
    assert record.recorded_by == "staff@example.gov"
    assert record.artifact_sha256 == prepared.sha256
    assert record.artifact_bytes == prepared.size
    assert record.source_sha256 == SOURCE.sha256
    assert record.source_label == SOURCE.label
    assert session.commits == 1
    final = resolve_inside_root(store, record.relative_path)
    assert final.is_file()
    assert not prepared.staging_path.exists()
    assert verify_artifact_file(store, record) == prepared.sha256


async def test_accept_artifact_is_idempotent_for_the_same_claim(store: ArtifactStore) -> None:
    task = make_task()
    session = FakeSession()
    first = await accept_artifact(session, task, prepare_artifact(proposal(), store))
    second = await accept_artifact(session, task, prepare_artifact(proposal(), store))

    assert first.artifact_id == second.artifact_id
    assert len(await artifacts_for_task(session, task.task_id)) == 1
    assert session.commits == 1


async def test_conflicting_content_for_the_same_name_is_refused(store: ArtifactStore) -> None:
    task = make_task()
    session = FakeSession()
    await accept_artifact(session, task, prepare_artifact(proposal(), store))

    conflicting = prepare_artifact(proposal(content=b"different bytes"), store)
    with pytest.raises(ArtifactRefused) as excinfo:
        await accept_artifact(session, task, conflicting)
    assert excinfo.value.reason == "artifact-name-conflict"
    assert not conflicting.staging_path.exists()


@pytest.mark.parametrize(
    "overrides, reason",
    [
        ({"status": "cancelled", "claim_token": None, "lease_expires_at": None},
         "artifact-not-running"),
        ({"status": "succeeded", "lease_expires_at": None}, "artifact-not-running"),
        ({"claim_token": None}, "artifact-claim-missing"),
        ({"audit_subject_id": None}, "artifact-not-attributed"),
    ],
)
async def test_non_running_unclaimed_or_unattributed_jobs_are_refused(
    store: ArtifactStore, overrides: dict, reason: str
) -> None:
    task = make_task(**overrides)
    session = FakeSession()
    prepared = prepare_artifact(proposal(), store)

    with pytest.raises(ArtifactRefused) as excinfo:
        await accept_artifact(session, task, prepared)
    assert excinfo.value.reason == reason
    assert not prepared.staging_path.exists()
    assert session.commits == 0
    assert published_files(store) == []


async def test_stale_claim_is_refused_leaving_no_durable_artifact(store: ArtifactStore) -> None:
    task = make_task()
    session = FakeSession(stale=True)
    prepared = prepare_artifact(proposal(), store)

    with pytest.raises(StaleTaskClaim):
        await accept_artifact(session, task, prepared)

    assert not prepared.staging_path.exists()
    assert session.commits == 0
    assert session.rollbacks == 1
    assert published_files(store) == []
    assert await artifacts_for_task(session, task.task_id) == []


async def test_stale_claim_cannot_reuse_its_own_earlier_acceptance(store: ArtifactStore) -> None:
    task = make_task()
    session = FakeSession()
    record = await accept_artifact(session, task, prepare_artifact(proposal(), store))

    session.stale = True
    with pytest.raises(StaleTaskClaim):
        await accept_artifact(session, task, prepare_artifact(proposal(), store))
    assert [row.artifact_id for row in session.rows] == [record.artifact_id]
    assert session.commits == 1


async def test_explicit_actor_is_accepted_when_the_task_has_no_subject(
    store: ArtifactStore,
) -> None:
    task = make_task(audit_subject_id=None)
    session = FakeSession()
    record = await accept_artifact(
        session, task, prepare_artifact(proposal(), store), recorded_by="clerk@example.gov"
    )
    assert record.recorded_by == "clerk@example.gov"


def test_tampered_artifact_file_is_detected(store: ArtifactStore) -> None:
    session = FakeSession()

    async def publish() -> JobArtifact:
        return await accept_artifact(session, make_task(), prepare_artifact(proposal(), store))

    record = asyncio.run(publish())
    resolve_inside_root(store, record.relative_path).write_bytes(b"tampered!")
    with pytest.raises(ArtifactRefused) as excinfo:
        verify_artifact_file(store, record)
    assert excinfo.value.reason == "artifact-hash-mismatch"


def test_unknown_refusal_reason_is_rejected() -> None:
    assert len(REFUSAL_REASONS) >= 12
    with pytest.raises(ValueError):
        ArtifactRefused("not-a-real-reason")


def test_artifact_namespace_is_importable_and_exported() -> None:
    import civiccore.tasks as tasks

    for name in (
        "ArtifactProposal",
        "ArtifactRefused",
        "ArtifactStore",
        "JobArtifact",
        "SourceBinding",
        "accept_artifact",
        "artifacts_for_task",
        "prepare_artifact",
        "resolve_inside_root",
        "verify_artifact_file",
    ):
        assert name in tasks.__all__, name
        assert hasattr(tasks, name), name
