"""Smoke test - proves the package is importable and version-tagged."""

from pathlib import Path
import tomllib


def test_import_civiccore() -> None:
    import civiccore

    assert civiccore.__version__ == "1.3.0.dev1"
    assert civiccore.roles_grant_access
    assert civiccore.access_level_allows
    assert civiccore.filter_records_by_access_level
    assert civiccore.AuditHashChain
    assert civiccore.PersistedAuditLogEntry
    assert callable(civiccore.compute_persisted_audit_hash)
    assert callable(civiccore.verify_persisted_audit_chain)
    assert civiccore.SourceReference
    assert civiccore.ExportManifest
    assert civiccore.ExportBundle
    assert civiccore.CityProfile
    assert civiccore.reciprocal_rank_fusion
    assert civiccore.import_meeting_payload
    assert civiccore.DiscoveredRecord
    assert civiccore.FetchedDocument
    assert civiccore.SourceMaterial
    assert civiccore.validate_cited_sentences
    assert civiccore.build_deadline_plan
    assert civiccore.evaluate_notice_compliance
    assert civiccore.encrypt_json
    assert civiccore.LocalTask
    assert civiccore.enqueue_local_task
    assert civiccore.claim_next_local_task
    assert civiccore.run_one_local_task
    assert civiccore.validate_url_host
    assert civiccore.normalize_trusted_proxy_cidrs
    assert civiccore.is_trusted_proxy_ip
    assert civiccore.validate_cron_expression
    assert civiccore.compute_next_sync_at


def test_package_metadata_marks_v1_as_provisional_recovery_line() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "1.3.0.dev1"
    assert "Development Status :: 4 - Beta" in pyproject["project"]["classifiers"]
    assert "Development Status :: 5 - Production/Stable" not in pyproject["project"]["classifiers"]
    assert "Development Status :: 2 - Pre-Alpha" not in pyproject["project"]["classifiers"]
