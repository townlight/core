"""Tests for TownlightCore Windows-local platform contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from townlight_core.platform import (
    BackupManifest,
    LocalRuntimeProfile,
    LocalTaskEnvelope,
    ModuleManifest,
    PlatformHealthCheck,
    RuntimeActionResult,
    TaskRetryPolicy,
    build_backup_manifest,
    build_module_registry,
    can_run_task,
    plan_restore,
    record_task_attempt,
    summarize_platform_health,
    summarize_task_queue,
    validate_backup_manifest,
)


def _module_manifest(module_id: str = "townlight_meetings", **overrides) -> ModuleManifest:
    data = {
        "module_id": module_id,
        "name": "TownlightMeetings",
        "version": "1.0.0",
        "package_name": "townlight_meetings",
        "townlight_core_min_version": "1.2.0",
        "surfaces": ["staff", "admin"],
        "install_profiles": ["windows_local"],
        "permissions": [
            {
                "key": "meeting-editor",
                "label": "Meeting editor",
                "description": "Can prepare meeting materials.",
                "roles": ["clerk_admin", "meeting_editor"],
            }
        ],
        "routes": [
            {
                "id": "meetings",
                "path": "/meetings",
                "label": "Meetings & Notices",
                "permission": "meeting-editor",
            }
        ],
        "health_checks": [
            {
                "id": "database-ready",
                "label": "Database ready",
                "description": "Checks the local database schema.",
                "repair_action": "repair-database",
            }
        ],
        "services": [
            {
                "id": "api",
                "service_type": "local-api",
                "description": "Local module API",
                "health_check_id": "database-ready",
            }
        ],
        "migrations": [
            {
                "id": "initial-schema",
                "description": "Create local TownlightMeetings tables.",
                "owner_schema": "townlight_meetings",
            }
        ],
        "backup_hooks": [
            {
                "id": "module-data",
                "label": "Module data",
                "includes": ["townlight_meetings/**"],
            }
        ],
        "model_requirements": [
            {
                "id": "agenda-drafts",
                "provider": "ollama",
                "model_name": "gemma-4-12b-it-qat-q4_0",
                "minimum_context_tokens": 8192,
            }
        ],
        "runtime_requirements": [
            {
                "kind": "postgres",
                "name": "Portable PostgreSQL",
                "description": "Local PostgreSQL runtime managed by the desktop shell.",
                "required": True,
            },
            {
                "kind": "ollama",
                "name": "Local Ollama runtime",
                "description": "Local model runner managed by the desktop shell.",
                "required": True,
            },
        ],
    }
    data.update(overrides)
    return ModuleManifest.model_validate(data)


def test_windows_manifest_rejects_docker_wsl_and_terminal_requirements() -> None:
    for kind in ("docker", "wsl", "linux_shell", "terminal"):
        with pytest.raises(ValueError, match="Windows local profile"):
            _module_manifest(
                runtime_requirements=[
                    {
                        "kind": kind,
                        "name": kind,
                        "description": "Not allowed for clerk installs.",
                        "required": True,
                    }
                ]
            )


def test_module_registry_blocks_missing_required_dependencies() -> None:
    manifest = _module_manifest(
        dependencies=[{"module_id": "townlight_records", "required": True}]
    )

    registry = build_module_registry(
        [manifest],
        townlight_core_version="1.2.0",
        selected_module_ids={"townlight_meetings"},
    )

    entry = registry.entries[0]
    assert registry.townlight_core_locked is True
    assert entry.status == "blocked"
    assert entry.enabled is False
    assert "townlight_records" in (entry.reason or "")


def test_module_registry_enables_valid_windows_local_module() -> None:
    manifest = _module_manifest()

    registry = build_module_registry([manifest], townlight_core_version="1.2.0")

    assert registry.enabled_module_ids == ["townlight_meetings"]
    assert registry.blocked_module_ids == []
    assert registry.entries[0].manifest.routes[0].label == "Meetings & Notices"


def test_platform_health_summary_uses_plain_english_blocking_action() -> None:
    checks = [
        PlatformHealthCheck(
            component="postgres",
            label="Local database",
            status="ok",
            message="Database is reachable.",
            next_action="No action needed.",
        ),
        PlatformHealthCheck(
            component="model",
            label="Gemma model",
            status="blocked",
            message="The local model is missing.",
            next_action="Open Model Setup and download the approved local model.",
            blocking=True,
            admin_detail="Expected Gemma 4 12B QAT Q4_0.",
        ),
    ]

    summary = summarize_platform_health(checks)

    assert summary.status == "blocked"
    assert summary.is_release_blocked is True
    assert summary.blocked_components == ["model"]
    assert summary.next_action == "Open Model Setup and download the approved local model."


def test_local_task_retry_contract_has_no_external_runtime_assumption() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
    task = LocalTaskEnvelope(
        task_id="packet-export-1",
        module_id="townlight_meetings",
        task_type="packet_export",
    )

    result = record_task_attempt(
        task,
        success=False,
        error="PDF render failed",
        now=now,
        policy=TaskRetryPolicy(max_attempts=3, base_delay_seconds=60),
    )

    assert result.task.status == "retry_wait"
    assert result.retry_at == now + timedelta(seconds=60)
    assert can_run_task(result.task, now=now + timedelta(seconds=59)) is False
    assert can_run_task(result.task, now=now + timedelta(seconds=60)) is True

    summary = summarize_task_queue([result.task])
    assert summary.counts == {"retry_wait": 1}
    assert summary.blocked is False


def test_local_task_exhaustion_is_blocking() -> None:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
    task = LocalTaskEnvelope(
        task_id="records-export-1",
        module_id="townlight_records",
        task_type="records_export",
        attempt_count=1,
    )

    result = record_task_attempt(
        task,
        success=False,
        error="Export destination unavailable",
        now=now,
        policy=TaskRetryPolicy(max_attempts=2, base_delay_seconds=1),
    )

    assert result.task.status == "failed"
    assert summarize_task_queue([result.task]).blocked is True


def test_backup_manifest_validates_hashes_and_restore_safety(tmp_path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "townlight_meetings").mkdir()
    payload = data_root / "townlight_meetings" / "meetings.json"
    payload.write_text('{"meeting":"Regular Council"}', encoding="utf-8")

    manifest = build_backup_manifest(
        root=data_root,
        files=[payload],
        backup_id="backup-1",
        city_profile_id="sampleville",
        townlight_core_version="1.2.0",
        module_id="townlight_meetings",
    )

    assert isinstance(manifest, BackupManifest)
    assert validate_backup_manifest(manifest, root=data_root).valid is True

    restore_root = tmp_path / "restore"
    restore_root.mkdir()
    plan = plan_restore(manifest, backup_root=data_root, restore_root=restore_root)

    assert plan.ready is True
    assert plan.actions[0].status == "ready"

    payload.write_text("tampered", encoding="utf-8")
    tampered = validate_backup_manifest(manifest, root=data_root)
    assert tampered.valid is False
    assert tampered.hash_mismatches == ["townlight_meetings/meetings.json"]


def test_restore_plan_blocks_overwrite_by_default(tmp_path) -> None:
    backup_root = tmp_path / "backup"
    restore_root = tmp_path / "restore"
    (backup_root / "townlight_code").mkdir(parents=True)
    (restore_root / "townlight_code").mkdir(parents=True)
    source = backup_root / "townlight_code" / "code.json"
    target = restore_root / "townlight_code" / "code.json"
    source.write_text('{"title":"Code"}', encoding="utf-8")
    target.write_text("existing", encoding="utf-8")

    manifest = build_backup_manifest(
        root=backup_root,
        files=[source],
        backup_id="backup-2",
        city_profile_id="sampleville",
        townlight_core_version="1.2.0",
        module_id="townlight_code",
    )
    plan = plan_restore(manifest, backup_root=backup_root, restore_root=restore_root)

    assert plan.ready is False
    assert plan.actions[0].status == "would_overwrite"


def test_runtime_profile_and_action_result_are_local_first(tmp_path) -> None:
    registry = build_module_registry([_module_manifest()], townlight_core_version="1.2.0")

    profile = LocalRuntimeProfile(
        profile_id="sampleville",
        city_name="Sampleville",
        data_root=tmp_path / "data",
        backup_root=tmp_path / "backups",
        module_registry=registry,
        network_allowed_for=["model_download"],
    )
    result = RuntimeActionResult(
        action="first_run",
        status="succeeded",
        title="Setup complete",
        message="Townlight is ready on this computer.",
    )

    assert profile.local_only is True
    assert profile.module_registry.enabled_module_ids == ["townlight_meetings"]
    assert result.status == "succeeded"
