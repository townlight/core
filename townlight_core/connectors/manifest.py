"""Offline connector and export manifest primitives.

These models describe file-based imports and static export bundles only. They
intentionally do not provide live connector sync, credentials, adapters, or
write-back runtime behavior.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ImportPurpose = Literal["file_drop_import", "csv_import", "geojson_import"]
ExportPurpose = Literal["static_export_bundle"]
ManifestPurpose = ImportPurpose | ExportPurpose

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class ManifestValidationError(ValueError):
    """Raised when a manifest is malformed or does not match files on disk."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_string(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


class ManifestFile(BaseModel):
    """A file entry recorded in an import or export manifest."""

    path: str
    byte_size: int = Field(ge=0)
    sha256: str
    media_type: str | None = None
    description: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("path")
    @classmethod
    def _validate_relative_path(cls, value: str) -> str:
        cleaned = _clean_string(value.replace("\\", "/"), "path")
        candidate = Path(cleaned)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("path must be a relative path within the manifest bundle")
        return cleaned

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not _SHA256_RE.fullmatch(cleaned):
            raise ValueError("sha256 must be a 64-character lowercase hex digest")
        return cleaned

    @field_validator("media_type", "description")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_string(value, "text field")


class _ManifestBase(BaseModel):
    manifest_version: str = "1.0"
    module_name: str
    module_version: str
    townlight_core_version: str
    purpose: ManifestPurpose
    source_files: list[ManifestFile] = Field(default_factory=list)
    generated_files: list[ManifestFile] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("manifest_version", "module_name", "module_version", "townlight_core_version")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        return _clean_string(value, "required text field")

    @field_validator("limitations")
    @classmethod
    def _validate_limitations(cls, value: list[str]) -> list[str]:
        cleaned = [_clean_string(item, "limitation") for item in value]
        if not cleaned:
            raise ValueError("limitations must include at least one explicit limitation")
        return cleaned

    @model_validator(mode="after")
    def _validate_files(self) -> "_ManifestBase":
        files = self.source_files + self.generated_files
        if not files:
            raise ValueError("manifest must include at least one source or generated file")

        paths = [file.path for file in files]
        duplicates = sorted({path for path in paths if paths.count(path) > 1})
        if duplicates:
            raise ValueError(f"manifest contains duplicate file paths: {', '.join(duplicates)}")
        return self

    @property
    def files(self) -> tuple[ManifestFile, ...]:
        """Return source and generated files in manifest order."""

        return tuple(self.source_files + self.generated_files)


class ImportManifest(_ManifestBase):
    """Manifest for offline file-drop, CSV, or GeoJSON imports."""

    purpose: ImportPurpose

    @model_validator(mode="after")
    def _validate_import_files(self) -> "ImportManifest":
        if not self.source_files:
            raise ValueError("import manifests must include at least one source file")
        return self


class ExportManifest(_ManifestBase):
    """Manifest for an offline static export bundle."""

    purpose: ExportPurpose = "static_export_bundle"

    @model_validator(mode="after")
    def _validate_export_files(self) -> "ExportManifest":
        if not self.generated_files:
            raise ValueError("export manifests must include at least one generated file")
        return self


def _load_manifest_data(manifest: str | Path | dict[str, Any] | _ManifestBase) -> dict[str, Any]:
    if isinstance(manifest, _ManifestBase):
        return manifest.model_dump(mode="json")
    if isinstance(manifest, dict):
        return manifest

    manifest_path = Path(manifest)
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestValidationError(f"Unable to read manifest: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"Manifest is not valid JSON: {manifest_path}") from exc


def _model_for_purpose(data: dict[str, Any]) -> type[ImportManifest] | type[ExportManifest]:
    if data.get("purpose") == "static_export_bundle":
        return ExportManifest
    return ImportManifest


def _verify_manifest_files(manifest: _ManifestBase, base_path: Path) -> None:
    for file_entry in manifest.files:
        file_path = base_path / file_entry.path
        if not file_path.is_file():
            raise ManifestValidationError(f"Manifest file is missing: {file_entry.path}")

        actual_size = file_path.stat().st_size
        if actual_size != file_entry.byte_size:
            raise ManifestValidationError(
                f"Manifest byte size mismatch for {file_entry.path}: "
                f"expected {file_entry.byte_size}, got {actual_size}"
            )

        actual_sha256 = _sha256_file(file_path)
        if actual_sha256 != file_entry.sha256:
            raise ManifestValidationError(
                f"Manifest checksum mismatch for {file_entry.path}: "
                f"expected {file_entry.sha256}, got {actual_sha256}"
            )


def validate_manifest(
    manifest: str | Path | dict[str, Any] | ImportManifest | ExportManifest,
    *,
    base_path: str | Path | None = None,
    expected_townlight_core_version: str | None = None,
) -> ImportManifest | ExportManifest:
    """Validate a manifest payload and, when requested, its files on disk.

    Args:
        manifest: Manifest model, mapping, JSON string path, or JSON Path.
        base_path: Optional directory used to verify file existence, byte sizes,
            and SHA-256 checksums.
        expected_townlight_core_version: Optional exact Townlight Core version to require.

    Raises:
        ManifestValidationError: If schema validation or file verification fails.
    """

    data = _load_manifest_data(manifest)
    model_cls = _model_for_purpose(data)
    try:
        validated = model_cls.model_validate(data)
    except ValidationError as exc:
        raise ManifestValidationError(str(exc)) from exc

    if expected_townlight_core_version is not None and (
        validated.townlight_core_version != expected_townlight_core_version
    ):
        raise ManifestValidationError(
            "Manifest Townlight Core version mismatch: "
            f"expected {expected_townlight_core_version}, got {validated.townlight_core_version}"
        )

    if base_path is not None:
        _verify_manifest_files(validated, Path(base_path))

    return validated


__all__ = [
    "ExportManifest",
    "ImportManifest",
    "ManifestFile",
    "ManifestValidationError",
    "validate_manifest",
]
