from __future__ import annotations

import socket

import pytest

from townlight_core.connectors.manifest import ManifestValidationError
from townlight_core.exports import (
    BundleFile,
    ExportBundle,
    build_sha256sums,
    validate_bundle,
    write_manifest,
)


def _make_bundle(tmp_path) -> ExportBundle:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "cases.csv").write_text("case_id,status\nA-1,open\n", encoding="utf-8")
    (reports / "summary.json").write_text('{"total":1}\n', encoding="utf-8")

    return ExportBundle(
        module_name="townlight_records",
        module_version="0.3.0",
        files=[
            BundleFile.from_path(tmp_path, "reports/cases.csv"),
            BundleFile.from_path(tmp_path, "reports/summary.json"),
        ],
        limitations=["Static files only; no server or live connector required."],
    )


def test_write_manifest_build_sha256sums_and_validate_bundle(tmp_path) -> None:
    bundle = _make_bundle(tmp_path)

    manifest = write_manifest(tmp_path, bundle)
    sums = build_sha256sums(tmp_path, bundle.files)

    assert (tmp_path / "manifest.json").is_file()
    assert (tmp_path / "SHA256SUMS.txt").is_file()
    assert "reports/cases.csv" in sums
    assert validate_bundle(tmp_path) == manifest


def test_validate_bundle_detects_file_checksum_mismatch(tmp_path) -> None:
    bundle = _make_bundle(tmp_path)
    write_manifest(tmp_path, bundle)
    build_sha256sums(tmp_path, bundle.files)

    (tmp_path / "reports" / "cases.csv").write_text("case_id,status\nA-1,closed\n", encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="byte size mismatch|checksum mismatch"):
        validate_bundle(tmp_path)


def test_validate_bundle_detects_missing_file(tmp_path) -> None:
    bundle = _make_bundle(tmp_path)
    write_manifest(tmp_path, bundle)
    build_sha256sums(tmp_path, bundle.files)

    (tmp_path / "reports" / "summary.json").unlink()

    with pytest.raises(ManifestValidationError, match="missing"):
        validate_bundle(tmp_path)


def test_validate_bundle_detects_sha256sums_count_mismatch(tmp_path) -> None:
    bundle = _make_bundle(tmp_path)
    write_manifest(tmp_path, bundle)
    build_sha256sums(tmp_path, [bundle.files[0]])

    with pytest.raises(ManifestValidationError, match="count mismatch"):
        validate_bundle(tmp_path)


def test_export_bundle_utilities_are_offline(monkeypatch, tmp_path) -> None:
    def fail_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("export bundle utilities must not open network sockets")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    bundle = _make_bundle(tmp_path)

    write_manifest(tmp_path, bundle)
    build_sha256sums(tmp_path, bundle.files)

    assert validate_bundle(tmp_path).purpose == "static_export_bundle"
