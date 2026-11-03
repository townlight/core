from __future__ import annotations

import hashlib
import json
import socket
from copy import deepcopy

import pytest

from townlight_core.testing import (
    DEMO_TOWN_CONTRACT_SCHEMA_VERSION,
    DEMO_TOWN_DEFAULT_SEED,
    DEMO_TOWN_FIXTURE_ID,
    DEMO_TOWN_FIXTURE_SHA256_V1,
    DEMO_TOWN_FIXTURE_VERSION,
    DEMO_TOWN_GENERATION_MODE,
    DEMO_TOWN_NAME,
    DEMO_TOWN_PROVENANCE_MODES,
    DEMO_TOWN_WATERMARK,
    assert_demo_town_fixture_safe,
    demo_town_fixture,
    demo_town_fixture_contract,
    validate_demo_town_fixture,
)


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _reseal(fixture: dict[str, object]) -> None:
    fixture["manifest"]["artifact_hashes"] = {
        artifact_name: _canonical_sha256(fixture[key])
        for artifact_name, key in {
            "sources.json": "sources",
            "records.json": "records",
            "requests.json": "requests",
            "expected.json": "expected",
        }.items()
    }
    fixture.pop("fixture_sha256", None)
    fixture["fixture_sha256"] = _canonical_sha256(fixture)


def test_demo_town_contract_is_versioned_and_explicitly_fictional() -> None:
    fixture = demo_town_fixture()
    manifest = fixture["manifest"]

    assert manifest["schema_version"] == DEMO_TOWN_CONTRACT_SCHEMA_VERSION == "1.0.0"
    assert manifest["fixture_id"] == DEMO_TOWN_FIXTURE_ID
    assert manifest["fixture_version"] == DEMO_TOWN_FIXTURE_VERSION == "1.0.1"
    assert manifest["deterministic_seed"] == DEMO_TOWN_DEFAULT_SEED
    assert manifest["generation_mode"] == DEMO_TOWN_GENERATION_MODE == "static-canonical-v1"
    assert manifest["municipality"] == {
        "municipality_id": "redstone-valley-fictional",
        "name": DEMO_TOWN_NAME,
        "state": "CO",
        "timezone": "America/Denver",
        "population_band": "50,000-100,000",
        "fictional": True,
    }
    assert manifest["synthetic"] is True
    assert manifest["watermark"] == DEMO_TOWN_WATERMARK
    assert manifest["network_calls"] is False
    assert all(record["synthetic"] is True for record in fixture["records"])
    assert all(record["watermark"] == DEMO_TOWN_WATERMARK for record in fixture["records"])
    assert all(request["watermark"] == DEMO_TOWN_WATERMARK for request in fixture["requests"])


def test_demo_town_fixture_and_artifact_hashes_are_deterministic() -> None:
    first = demo_town_fixture()
    second = demo_town_fixture_contract().public_dict()

    assert first == second
    assert validate_demo_town_fixture(first) == ()
    for artifact_name, value in {
        "sources.json": first["sources"],
        "records.json": first["records"],
        "requests.json": first["requests"],
        "expected.json": first["expected"],
    }.items():
        assert first["manifest"]["artifact_hashes"][artifact_name] == _canonical_sha256(value)
    fixture_without_hash = dict(first)
    fixture_without_hash.pop("fixture_sha256")
    assert first["fixture_sha256"] == _canonical_sha256(fixture_without_hash)
    assert first["fixture_sha256"] == DEMO_TOWN_FIXTURE_SHA256_V1
    assert DEMO_TOWN_FIXTURE_SHA256_V1 == (
        "d9aaa79403cfca2711e8031439fbab8bf9f70a20b8afc293faef8edd683ffbd6"
    )
    assert len(first["fixture_sha256"]) == 64

    tampered = deepcopy(first)
    tampered["records"][0]["content"] += " tampered"
    errors = validate_demo_town_fixture(tampered)
    assert "records[0].content_sha256 does not match content" in errors
    assert "manifest.artifact_hashes do not match fixture artifacts" in errors
    assert "fixture_sha256 does not match fixture content" in errors


def test_demo_town_provenance_is_explicit_and_redistributable() -> None:
    fixture = demo_town_fixture()
    source = fixture["sources"][0]

    assert fixture["manifest"]["provenance_modes"] == list(DEMO_TOWN_PROVENANCE_MODES)
    assert DEMO_TOWN_PROVENANCE_MODES == ("fully-synthetic",)
    assert source["provenance_mode"] == "fully-synthetic"
    assert source["acquisition_method"] == "independent-authorship"
    assert source["canonical_url"] is None
    assert source["retrieved_at"] is None
    assert source["redistributable"] is True
    assert source["contains_personal_data"] is False
    assert source["allowed_uses"] == ["testing", "demonstration", "redistribution"]
    serialized = json.dumps(fixture).lower()
    assert "longmont" not in serialized
    assert "public media" not in serialized


def test_demo_town_defaults_are_secret_and_pii_free() -> None:
    fixture = demo_town_fixture()

    assert_demo_town_fixture_safe(fixture)
    assert all(record["contains_personal_data"] is False for record in fixture["records"])
    assert all(request["contains_personal_data"] is False for request in fixture["requests"])
    assert fixture["expected"]["pii"]["expected_findings"] == []

    personal_field = deepcopy(fixture)
    personal_field["requests"][0]["email"] = "synthetic-requester"
    with pytest.raises(ValueError, match="forbidden personal-data fields: email"):
        assert_demo_town_fixture_safe(personal_field)

    pii_pattern = deepcopy(fixture)
    pii_pattern["records"][0]["content"] += " contact person@example.invalid"
    with pytest.raises(ValueError, match="forbidden PII patterns: email_address"):
        assert_demo_town_fixture_safe(pii_pattern)

    personal_identity = deepcopy(fixture)
    personal_identity["requests"][0]["requester_name"] = "Jane Doe"
    personal_identity["requests"][0]["home_address"] = "123 Main Street"
    with pytest.raises(
        ValueError,
        match="forbidden personal-data fields: home_address, requester_name",
    ):
        assert_demo_town_fixture_safe(personal_identity)

    address_in_text = deepcopy(fixture)
    address_in_text["records"][0]["content"] += " Deliver to 123 Main Street."
    with pytest.raises(ValueError, match="forbidden PII patterns: postal_address"):
        assert_demo_town_fixture_safe(address_in_text)


def test_demo_town_generation_performs_no_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    attempted_connections: list[object] = []

    def reject_connection(*args: object, **kwargs: object) -> None:
        attempted_connections.append((args, kwargs))
        raise AssertionError("fixture generation attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", reject_connection)

    fixture = demo_town_fixture()

    assert attempted_connections == []
    assert fixture["manifest"]["network_calls"] is False
    assert all(source["canonical_url"] is None for source in fixture["sources"])


def test_demo_town_contract_supplies_records_workflow_ground_truth() -> None:
    fixture = demo_town_fixture()

    assert fixture["expected"]["counts"] == {"sources": 1, "records": 3, "requests": 1}
    assert fixture["expected"]["workflow"] == {
        "request_id": "rv-request-2026-0001",
        "status_sequence": [
            "received",
            "assigned",
            "searching",
            "in_review",
            "approved",
            "fulfilled",
            "closed",
        ],
        "human_approval_required": True,
    }
    assert fixture["expected"]["search"][0]["record_ids"] == [
        "rv-record-council-0001",
        "rv-record-trails-0001",
    ]


def test_demo_town_rejects_unimplemented_provenance_modes() -> None:
    fixture = deepcopy(demo_town_fixture())
    source = fixture["sources"][0]
    source["provenance_mode"] = "licensed-adaptation"
    source.pop("license_or_permission")
    source.pop("allowed_uses")
    _reseal(fixture)

    errors = validate_demo_town_fixture(fixture)

    assert "sources[0].provenance_mode must be 'fully-synthetic' in v1" in errors
    assert "sources[0].license_or_permission is required" in errors
    assert "sources[0].allowed_uses is required" in errors


def test_demo_town_rejects_duplicate_ids_and_broken_references() -> None:
    fixture = deepcopy(demo_town_fixture())
    duplicate = deepcopy(fixture["records"][0])
    duplicate["source_refs"] = ["missing-source"]
    fixture["records"].append(duplicate)
    fixture["requests"][0]["target_record_ids"] = ["missing-record"]
    fixture["expected"]["search"][0]["record_ids"] = ["missing-record"]
    fixture["expected"]["counts"] = {"sources": 99, "records": 99, "requests": 99}
    _reseal(fixture)

    errors = validate_demo_town_fixture(fixture)

    assert "records[3].record_id duplicates 'rv-record-council-0001'" in errors
    assert "records[3].source_refs contains unknown reference 'missing-source'" in errors
    assert "requests[0].target_record_ids contains unknown reference 'missing-record'" in errors
    assert "expected.search[0].record_ids contains unknown reference 'missing-record'" in errors
    assert any(error.startswith("expected.counts must equal") for error in errors)


def test_demo_town_rejects_workflow_and_pii_ground_truth_drift() -> None:
    fixture = deepcopy(demo_town_fixture())
    fixture["expected"]["workflow"]["request_id"] = "missing-request"
    fixture["expected"]["workflow"]["status_sequence"] = ["received", "closed"]
    fixture["expected"]["workflow"]["human_approval_required"] = False
    fixture["expected"]["pii"]["record_ids"] = ["rv-record-water-0001"]
    fixture["expected"]["pii"]["expected_findings"] = ["unexpected-person"]
    _reseal(fixture)

    errors = validate_demo_town_fixture(fixture)

    assert "expected.workflow.request_id must reference a fixture request" in errors
    assert "expected.workflow.status_sequence must equal the canonical sequence" in errors
    assert "expected.workflow.human_approval_required must be true" in errors
    assert "expected.pii.expected_findings must be empty for the v1 fixture" in errors
    assert "expected.pii.record_ids must cover every fixture record" in errors


def test_demo_town_v1_golden_hash_requires_a_versioned_content_change() -> None:
    fixture = deepcopy(demo_town_fixture())
    fixture["records"][0]["content"] += " Canonical content drift."
    fixture["records"][0]["content_sha256"] = _canonical_sha256(
        fixture["records"][0]["content"]
    )
    _reseal(fixture)

    errors = validate_demo_town_fixture(fixture)

    assert "fixture_sha256 does not match the pinned v1 golden fixture" in errors
