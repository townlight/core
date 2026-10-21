from __future__ import annotations

import hashlib

import pytest

from civiccore.connectors import (
    ExportManifest,
    ImportManifest,
    ManifestFile,
    ManifestValidationError,
    validate_manifest,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_validate_csv_import_manifest_with_file_checksum(tmp_path) -> None:
    payload = b"id,name\n1,Jane\n"
    source = tmp_path / "imports" / "people.csv"
    source.parent.mkdir()
    source.write_bytes(payload)

    manifest = ImportManifest(
        module_name="civicrecords",
        module_version="1.2.3",
        civiccore_version="0.3.0",
        purpose="csv_import",
        source_files=[
            ManifestFile(path="imports/people.csv", byte_size=len(payload), sha256=_sha256(payload))
        ],
        limitations=["Offline CSV import only; no live vendor sync."],
    )

    validated = validate_manifest(manifest.model_dump(mode="json"), base_path=tmp_path)

    assert isinstance(validated, ImportManifest)
    assert validated.purpose == "csv_import"
    assert validated.files[0].path == "imports/people.csv"


def test_validate_geojson_and_file_drop_import_purposes(tmp_path) -> None:
    geojson = b'{"type":"FeatureCollection","features":[]}'
    document = b"scanned permit"
    (tmp_path / "parcels.geojson").write_bytes(geojson)
    (tmp_path / "permit.pdf").write_bytes(document)

    geojson_manifest = {
        "module_name": "civiczone",
        "module_version": "0.3.0",
        "civiccore_version": "0.3.0",
        "purpose": "geojson_import",
        "source_files": [
            {
                "path": "parcels.geojson",
                "byte_size": len(geojson),
                "sha256": _sha256(geojson),
            }
        ],
        "limitations": ["Offline GeoJSON import only."],
    }
    file_drop_manifest = {
        "module_name": "civicrecords",
        "module_version": "0.3.0",
        "civiccore_version": "0.3.0",
        "purpose": "file_drop_import",
        "source_files": [
            {"path": "permit.pdf", "byte_size": len(document), "sha256": _sha256(document)}
        ],
        "limitations": ["Offline file drop only."],
    }

    assert validate_manifest(geojson_manifest, base_path=tmp_path).purpose == "geojson_import"
    assert validate_manifest(file_drop_manifest, base_path=tmp_path).purpose == "file_drop_import"


def test_validate_static_export_manifest_with_generated_file(tmp_path) -> None:
    content = b"case_id,status\nA-1,open\n"
    export = tmp_path / "cases.csv"
    export.write_bytes(content)

    manifest = {
        "module_name": "civicrecords",
        "module_version": "0.3.0",
        "civiccore_version": "0.3.0",
        "purpose": "static_export_bundle",
        "generated_files": [
            {"path": "cases.csv", "byte_size": len(content), "sha256": _sha256(content)}
        ],
        "limitations": ["Static export bundle; validates offline without a running server."],
    }

    validated = validate_manifest(manifest, base_path=tmp_path)

    assert isinstance(validated, ExportManifest)
    assert validated.generated_files[0].sha256 == _sha256(content)


def test_manifest_detects_checksum_size_missing_and_version_mismatch(tmp_path) -> None:
    data = b"original"
    file_path = tmp_path / "data.csv"
    file_path.write_bytes(data)

    manifest = {
        "module_name": "civicrecords",
        "module_version": "0.3.0",
        "civiccore_version": "0.3.0",
        "purpose": "csv_import",
        "source_files": [{"path": "data.csv", "byte_size": len(data), "sha256": _sha256(data)}],
        "limitations": ["Offline import only."],
    }
    assert validate_manifest(manifest, base_path=tmp_path)

    file_path.write_bytes(b"changed")
    with pytest.raises(ManifestValidationError, match="byte size mismatch|checksum mismatch"):
        validate_manifest(manifest, base_path=tmp_path)

    file_path.unlink()
    with pytest.raises(ManifestValidationError, match="missing"):
        validate_manifest(manifest, base_path=tmp_path)

    with pytest.raises(ManifestValidationError, match="Townlight Core version mismatch"):
        validate_manifest(manifest, expected_civiccore_version="9.9.9")


def test_manifest_models_do_not_expose_live_connector_runtime_behavior() -> None:
    manifest_attrs = set(dir(ImportManifest)) | set(dir(ExportManifest))

    assert "sync" not in manifest_attrs
    assert "connect" not in manifest_attrs
    assert "credentials" not in ImportManifest.model_fields
    assert "vendor_adapter" not in ExportManifest.model_fields
