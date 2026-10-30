# SPDX-License-Identifier: AGPL-3.0-only
"""ADR-0010 must record the artifact-adapter contract without rewriting earlier ADRs."""

from __future__ import annotations

from pathlib import Path

import civiccore.tasks.artifacts as artifacts


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_artifact_adr_records_trust_boundary_and_non_claims() -> None:
    current = (REPO_ROOT / "docs/adr/ADR-0010-claim-bound-artifacts.md").read_text(
        encoding="utf-8"
    )

    assert "Implemented in the private beta candidate" in current
    assert "not released" in current
    assert "claim_token" in current
    assert "StaleTaskClaim" in current
    assert "civiccore_job_artifacts" in current
    assert "append-only" in current
    assert "restore-from-backup" in current
    assert "**no** transcription" in current
    # It must not claim more than was tested.
    assert "Core HTTP/CLI surface" in current
    assert "9/9 checks" in current


def test_artifact_doc_states_path_and_hash_rules() -> None:
    doc = (REPO_ROOT / "docs/job-artifacts.md").read_text(encoding="utf-8")

    for phrase in (
        "Trust boundary",
        "Path handling",
        "Hashes and publication",
        "Supported scope",
        "What this does not do",
        "realpath",
        "artifact-hash-mismatch",
    ):
        assert phrase in doc, phrase


def test_historical_adr_text_is_preserved() -> None:
    for name in (
        "ADR-0001-defer-civiccore-catalog.md",
        "ADR-0004-beta-shared-catalog.md",
        "ADR-0006-rule-version-history.md",
        "ADR-0008-beta-module-inventory.md",
        "ADR-0009-department-scoped-authority.md",
    ):
        text = (REPO_ROOT / "docs" / "adr" / name).read_text(encoding="utf-8")
        assert "Status:" in text, name

    index = (REPO_ROOT / "docs/adr/index.md").read_text(encoding="utf-8")
    assert "ADR-0010-claim-bound-artifacts.md" in index
    assert "ADR-0001-defer-civiccore-catalog.md" in index
    assert "ADR-0009-department-scoped-authority.md" in index


def test_artifact_module_documents_the_non_claims_it_must_uphold() -> None:
    docstring = " ".join((artifacts.__doc__ or "").split())

    assert "Trust boundary" in docstring
    assert "claim_token" in docstring
    assert "StaleTaskClaim" in docstring
    assert "not a second job engine" in docstring
    assert "performs no transcription" in docstring
    assert "os.replace" in docstring


def test_artifact_contract_is_importable_from_the_tasks_namespace() -> None:
    import civiccore.tasks as tasks

    for name in (
        "ArtifactProposal",
        "ArtifactRefused",
        "ArtifactStore",
        "JobArtifact",
        "PreparedArtifact",
        "SourceBinding",
        "accept_artifact",
        "artifacts_for_task",
        "discard_prepared",
        "prepare_artifact",
        "resolve_inside_root",
        "verify_artifact_file",
    ):
        assert name in tasks.__all__, name
        assert hasattr(tasks, name), name


def test_queue_require_active_claim_is_exported_without_a_second_engine() -> None:
    import civiccore.platform as platform

    assert "require_active_claim" in platform.__all__
    assert hasattr(platform, "require_active_claim")
    source = (REPO_ROOT / "civiccore/platform/task_queue.py").read_text(encoding="utf-8")
    # It must be a read-only fence over the existing ownership helper.
    assert "async def require_active_claim(" in source
    assert "row = await _owned_task(session, task_id, claim_token, now)" in source
