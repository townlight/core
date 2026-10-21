"""Backup and restore manifest contracts for local Townlight installs."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RestoreActionStatus = Literal["ready", "missing", "hash_mismatch", "would_overwrite"]


class BackupItem(BaseModel):
    """One file captured in a local backup."""

    model_config = ConfigDict(extra="forbid")

    module_id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    relative_path: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    required: bool = True


class BackupManifest(BaseModel):
    """Versioned backup manifest for a Townlight local profile."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    backup_id: str = Field(min_length=1)
    city_profile_id: str = Field(min_length=1)
    civiccore_version: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    modules: list[str] = Field(default_factory=list)
    items: list[BackupItem]


class BackupValidationResult(BaseModel):
    """Result of checking a backup manifest against files on disk."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    missing: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)


class BackupRestoreAction(BaseModel):
    """One file restore action and its safety status."""

    model_config = ConfigDict(extra="forbid")

    source_relative_path: str
    target_relative_path: str
    status: RestoreActionStatus
    message: str


class BackupRestorePlan(BaseModel):
    """A non-destructive restore plan."""

    model_config = ConfigDict(extra="forbid")

    ready: bool
    actions: list[BackupRestoreAction]
    blocked_reason: str | None = None


def build_backup_manifest(
    *,
    root: Path,
    files: list[Path],
    backup_id: str,
    city_profile_id: str,
    civiccore_version: str,
    module_id: str,
) -> BackupManifest:
    """Build a checksum manifest for files under a local data root."""

    resolved_root = root.resolve()
    items: list[BackupItem] = []
    for path in files:
        resolved_path = path.resolve()
        _assert_inside(resolved_path, resolved_root)
        if not resolved_path.is_file():
            raise ValueError(f"backup item is not a file: {resolved_path}")
        relative_path = resolved_path.relative_to(resolved_root).as_posix()
        items.append(
            BackupItem(
                module_id=module_id,
                relative_path=relative_path,
                size_bytes=resolved_path.stat().st_size,
                sha256=_sha256_file(resolved_path),
            )
        )

    return BackupManifest(
        backup_id=backup_id,
        city_profile_id=city_profile_id,
        civiccore_version=civiccore_version,
        modules=sorted({module_id for _item in items}),
        items=sorted(items, key=lambda item: item.relative_path),
    )


def validate_backup_manifest(manifest: BackupManifest, *, root: Path) -> BackupValidationResult:
    """Check that a manifest still matches a backup directory."""

    resolved_root = root.resolve()
    missing: list[str] = []
    mismatches: list[str] = []
    for item in manifest.items:
        path = (resolved_root / item.relative_path).resolve()
        _assert_inside(path, resolved_root)
        if not path.is_file():
            missing.append(item.relative_path)
            continue
        if _sha256_file(path) != item.sha256:
            mismatches.append(item.relative_path)

    return BackupValidationResult(
        valid=not missing and not mismatches,
        missing=missing,
        hash_mismatches=mismatches,
    )


def plan_restore(
    manifest: BackupManifest,
    *,
    backup_root: Path,
    restore_root: Path,
    overwrite: bool = False,
) -> BackupRestorePlan:
    """Return a non-destructive restore plan for a backup manifest."""

    resolved_backup_root = backup_root.resolve()
    resolved_restore_root = restore_root.resolve()
    actions: list[BackupRestoreAction] = []

    for item in manifest.items:
        source = (resolved_backup_root / item.relative_path).resolve()
        target = (resolved_restore_root / item.relative_path).resolve()
        _assert_inside(source, resolved_backup_root)
        _assert_inside(target, resolved_restore_root)

        if not source.is_file():
            actions.append(
                BackupRestoreAction(
                    source_relative_path=item.relative_path,
                    target_relative_path=item.relative_path,
                    status="missing",
                    message="Backup file is missing.",
                )
            )
            continue
        if _sha256_file(source) != item.sha256:
            actions.append(
                BackupRestoreAction(
                    source_relative_path=item.relative_path,
                    target_relative_path=item.relative_path,
                    status="hash_mismatch",
                    message="Backup file checksum does not match the manifest.",
                )
            )
            continue
        if target.exists() and not overwrite:
            actions.append(
                BackupRestoreAction(
                    source_relative_path=item.relative_path,
                    target_relative_path=item.relative_path,
                    status="would_overwrite",
                    message="Restore target already exists.",
                )
            )
            continue
        actions.append(
            BackupRestoreAction(
                source_relative_path=item.relative_path,
                target_relative_path=item.relative_path,
                status="ready",
                message="Ready to restore.",
            )
        )

    blockers = [action for action in actions if action.status != "ready"]
    return BackupRestorePlan(
        ready=not blockers,
        actions=actions,
        blocked_reason=None if not blockers else "Restore plan has file safety blockers.",
    )


def _assert_inside(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside the expected root: {path}") from exc


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
