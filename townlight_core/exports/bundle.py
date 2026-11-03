"""Utilities for static, offline Townlight Core export bundles."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from townlight_core import __version__ as TOWNLIGHT_CORE_VERSION
from townlight_core.connectors.manifest import (
    ExportManifest,
    ManifestFile,
    ManifestValidationError,
    validate_manifest,
)

MANIFEST_FILENAME = "manifest.json"
SHA256SUMS_FILENAME = "SHA256SUMS.txt"


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_relative_path(root: Path, path: str | Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        candidate = candidate.relative_to(root)
    return candidate.as_posix()


class BundleFile(ManifestFile):
    """A generated file included in a static export bundle."""

    @classmethod
    def from_path(cls, root: str | Path, path: str | Path) -> "BundleFile":
        root_path = Path(root)
        relative_path = _bundle_relative_path(root_path, path)
        file_path = root_path / relative_path
        return cls(
            path=relative_path,
            byte_size=file_path.stat().st_size,
            sha256=_sha256_file(file_path),
        )


class ExportBundle(BaseModel):
    """Description of a static export bundle that can be validated offline."""

    module_name: str
    module_version: str
    townlight_core_version: str = TOWNLIGHT_CORE_VERSION
    purpose: str = "static_export_bundle"
    files: list[BundleFile] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_static_bundle(self) -> "ExportBundle":
        if self.purpose != "static_export_bundle":
            raise ValueError("ExportBundle purpose must be static_export_bundle")
        if not self.files:
            raise ValueError("ExportBundle must include at least one file")
        if not self.limitations:
            raise ValueError("ExportBundle must include at least one explicit limitation")
        return self

    def to_manifest(self) -> ExportManifest:
        return ExportManifest(
            module_name=self.module_name,
            module_version=self.module_version,
            townlight_core_version=self.townlight_core_version,
            purpose="static_export_bundle",
            source_files=[],
            generated_files=[ManifestFile.model_validate(file.model_dump()) for file in self.files],
            limitations=self.limitations,
        )


def _discover_bundle_files(root: Path) -> list[Path]:
    excluded = {MANIFEST_FILENAME, SHA256SUMS_FILENAME}
    return sorted(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and path.name not in excluded
    )


def build_sha256sums(
    bundle_path: str | Path,
    files: Iterable[str | Path | BundleFile] | None = None,
    *,
    output_path: str | Path | None = SHA256SUMS_FILENAME,
) -> str:
    """Build SHA256SUMS.txt content for an export bundle.

    The function is fully offline. When ``output_path`` is not ``None``, the
    checksum file is written under ``bundle_path`` unless an absolute path is
    supplied.
    """

    root = Path(bundle_path)
    entries: list[tuple[str, str]] = []
    source_files = list(files) if files is not None else _discover_bundle_files(root)

    for item in source_files:
        if isinstance(item, BundleFile):
            entries.append((item.sha256, item.path))
            continue
        relative_path = _bundle_relative_path(root, item)
        entries.append((_sha256_file(root / relative_path), relative_path))

    content = "".join(f"{sha256}  {path}\n" for sha256, path in sorted(entries, key=lambda item: item[1]))

    if output_path is not None:
        destination = Path(output_path)
        if not destination.is_absolute():
            destination = root / destination
        destination.write_text(content, encoding="utf-8")

    return content


def write_manifest(
    bundle_path: str | Path,
    bundle: ExportBundle,
    *,
    manifest_name: str = MANIFEST_FILENAME,
) -> ExportManifest:
    """Write manifest.json for a static export bundle and return the manifest."""

    manifest = bundle.to_manifest()
    destination = Path(bundle_path) / manifest_name
    destination.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _read_sha256sums(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ManifestValidationError(f"Unable to read checksum file: {path}") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ManifestValidationError(f"Malformed checksum line {line_number}: {line!r}")
        sha256, file_path = parts[0].lower(), parts[1].strip()
        checksums[file_path] = sha256
    return checksums


def validate_bundle(
    bundle_path: str | Path,
    *,
    manifest_name: str = MANIFEST_FILENAME,
    checksums_name: str = SHA256SUMS_FILENAME,
) -> ExportManifest:
    """Validate manifest.json and SHA256SUMS.txt for a static export bundle."""

    root = Path(bundle_path)
    manifest = validate_manifest(root / manifest_name, base_path=root)
    if not isinstance(manifest, ExportManifest):
        raise ManifestValidationError("Bundle manifest must be an export manifest")

    checksum_entries = _read_sha256sums(root / checksums_name)
    manifest_entries = {file.path: file.sha256 for file in manifest.generated_files}

    missing = sorted(set(manifest_entries) - set(checksum_entries))
    extra = sorted(set(checksum_entries) - set(manifest_entries))
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing from SHA256SUMS: {', '.join(missing)}")
        if extra:
            details.append(f"extra in SHA256SUMS: {', '.join(extra)}")
        raise ManifestValidationError("Bundle file count mismatch: " + "; ".join(details))

    for path, expected_sha256 in manifest_entries.items():
        checksum_sha256 = checksum_entries[path]
        if checksum_sha256 != expected_sha256:
            raise ManifestValidationError(
                f"SHA256SUMS mismatch for {path}: expected {expected_sha256}, got {checksum_sha256}"
            )

    return manifest


__all__ = [
    "BundleFile",
    "ExportBundle",
    "build_sha256sums",
    "validate_bundle",
    "write_manifest",
]
