"""Smoke test - proves the package is importable and version-tagged."""

from pathlib import Path
import tomllib


def test_import_townlight_core() -> None:
    import townlight_core

    assert townlight_core.__version__ == "1.3.0.dev2"
    assert townlight_core.roles_grant_access
    assert townlight_core.access_level_allows
    assert townlight_core.filter_records_by_access_level
    assert townlight_core.AuditHashChain
    assert townlight_core.PersistedAuditLogEntry
    assert callable(townlight_core.compute_persisted_audit_hash)
    assert callable(townlight_core.verify_persisted_audit_chain)
    assert townlight_core.SourceReference
    assert townlight_core.ExportManifest
    assert townlight_core.ExportBundle
    assert townlight_core.CityProfile
    assert townlight_core.reciprocal_rank_fusion
    assert townlight_core.import_meeting_payload
    assert townlight_core.DiscoveredRecord
    assert townlight_core.FetchedDocument
    assert townlight_core.SourceMaterial
    assert townlight_core.validate_cited_sentences
    assert townlight_core.build_deadline_plan
    assert townlight_core.evaluate_notice_compliance
    assert townlight_core.encrypt_json
    assert townlight_core.LocalTask
    assert townlight_core.enqueue_local_task
    assert townlight_core.claim_next_local_task
    assert townlight_core.run_one_local_task
    assert townlight_core.validate_url_host
    assert townlight_core.normalize_trusted_proxy_cidrs
    assert townlight_core.is_trusted_proxy_ip
    assert townlight_core.validate_cron_expression
    assert townlight_core.compute_next_sync_at


def test_package_metadata_marks_v1_as_provisional_recovery_line() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "1.3.0.dev2"
    assert "Development Status :: 4 - Beta" in pyproject["project"]["classifiers"]
    assert "Development Status :: 5 - Production/Stable" not in pyproject["project"]["classifiers"]
    assert "Development Status :: 2 - Pre-Alpha" not in pyproject["project"]["classifiers"]
