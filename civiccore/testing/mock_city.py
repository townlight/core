"""Reusable no-network mock city integration contracts for Townlight modules."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from civiccore.connectors.delta import plan_vendor_delta_request
from civiccore.connectors.imports import SUPPORTED_CONNECTORS, import_meeting_payload

MOCK_CITY_NAME = "City of Brookfield"
MOCK_CITY_CHANGED_SINCE = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
MOCK_CITY_STAFF_ROLES = frozenset({"clerk_admin", "meeting_editor", "city_attorney"})
MOCK_CITY_IDP_KEY_ID = "brookfield-mock-idp-key-1"
MOCK_CITY_INTERFACE_STATUS = {
    "public-reference",
    "vendor-gated-contract",
}

DEMO_TOWN_CONTRACT_SCHEMA_VERSION = "1.0.0"
DEMO_TOWN_FIXTURE_VERSION = "1.0.0"
DEMO_TOWN_FIXTURE_ID = "redstone-valley-records-demo"
DEMO_TOWN_NAME = "Town of Redstone Valley (Fictional)"
# The v1 generator is intentionally static, not pseudo-random. This value is a
# canonical recipe identifier and is validated with the generation mode and
# golden hash so downstream tools can reject a different fixture selection.
DEMO_TOWN_DEFAULT_SEED = "townlight-records-demo-v1"
DEMO_TOWN_GENERATED_AT = "2026-08-17T00:00:00Z"
DEMO_TOWN_WATERMARK = "SYNTHETIC DEMONSTRATION DATA - NOT A REAL MUNICIPAL RECORD"
DEMO_TOWN_PROVENANCE_MODES = ("fully-synthetic",)
DEMO_TOWN_GENERATION_MODE = "static-canonical-v1"
DEMO_TOWN_FIXTURE_SHA256_V1 = "a9c242a3f2618a69d7effb1d0d17d2df06f6744c8c351bba4065d315c94575b4"
DEMO_TOWN_WORKFLOW_STATUSES = (
    "received",
    "assigned",
    "searching",
    "in_review",
    "approved",
    "fulfilled",
    "closed",
)

_DEMO_TOWN_PII_PATTERNS = {
    "email_address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "north_american_phone": re.compile(
        r"\b(?:\+?1[-. ]?)?(?:\(\d{3}\)|\d{3})[-. ]?\d{3}[-. ]?\d{4}\b"
    ),
    "postal_address": re.compile(
        r"\b\d{1,6}\s+[A-Z0-9][A-Z0-9 .'-]{1,40}\s"
        r"(?:STREET|ST|ROAD|RD|AVENUE|AVE|BOULEVARD|BLVD|DRIVE|DR|LANE|LN|COURT|CT|WAY)\b",
        re.IGNORECASE,
    ),
    "social_security_number": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}
_DEMO_TOWN_FORBIDDEN_PERSONAL_FIELDS = {
    "address",
    "email",
    "email_address",
    "full_name",
    "home_address",
    "legal_name",
    "mailing_address",
    "person_name",
    "phone",
    "phone_number",
    "postal_address",
    "requester_name",
    "resident_name",
    "social_security_number",
    "ssn",
    "street_address",
    "telephone",
}
_DEMO_TOWN_PERSONAL_NAME_FIELD_RE = re.compile(
    r"^(?:contact|employee|first|full|last|legal|person|preferred|requester|resident|staff)_name$"
)
_DEMO_TOWN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DEMO_TOWN_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class MockCityVendorContract:
    connector: str
    vendor_name: str
    interface_status: str
    method: str
    path: str
    auth_method: str
    delta_query_param: str
    sample_payload: dict[str, Any]
    notes: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "connector": self.connector,
            "vendor_name": self.vendor_name,
            "interface_status": self.interface_status,
            "method": self.method,
            "path": self.path,
            "auth_method": self.auth_method,
            "delta_query_param": self.delta_query_param,
            "sample_payload": self.sample_payload,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MockCityIdpContract:
    provider: str
    interface_status: str
    issuer: str
    audience: str
    authorization_url: str
    token_url: str
    jwks_path: str
    role_claims: tuple[str, ...]
    algorithms: tuple[str, ...]
    client_id: str
    redirect_uri: str
    staff_subject: str
    staff_email: str
    staff_roles: tuple[str, ...]
    notes: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "interface_status": self.interface_status,
            "issuer": self.issuer,
            "audience": self.audience,
            "authorization_url": self.authorization_url,
            "token_url": self.token_url,
            "jwks_path": self.jwks_path,
            "role_claims": list(self.role_claims),
            "algorithms": list(self.algorithms),
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "staff_subject": self.staff_subject,
            "staff_email": self.staff_email,
            "staff_roles": list(self.staff_roles),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MockCityBackupRetentionContract:
    city: str
    interface_status: str
    backup_scope: tuple[str, ...]
    restore_proof_required: bool
    manifest_required_fields: tuple[str, ...]
    retention_years: int
    restore_test_interval_days: int
    off_host_storage: str
    encryption_at_rest_required: bool
    immutable_retention_required: bool
    legal_hold_supported: bool
    approval_artifact: str
    notes: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "interface_status": self.interface_status,
            "backup_scope": list(self.backup_scope),
            "restore_proof_required": self.restore_proof_required,
            "manifest_required_fields": list(self.manifest_required_fields),
            "retention_years": self.retention_years,
            "restore_test_interval_days": self.restore_test_interval_days,
            "off_host_storage": self.off_host_storage,
            "encryption_at_rest_required": self.encryption_at_rest_required,
            "immutable_retention_required": self.immutable_retention_required,
            "legal_hold_supported": self.legal_hold_supported,
            "approval_artifact": self.approval_artifact,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MockCityContractCheck:
    connector: str
    ok: bool
    message: str
    fix: str
    normalized_external_meeting_id: str | None = None
    delta_request_url: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "connector": self.connector,
            "ok": self.ok,
            "message": self.message,
            "fix": self.fix,
            "normalized_external_meeting_id": self.normalized_external_meeting_id,
            "delta_request_url": self.delta_request_url,
        }


@dataclass(frozen=True)
class MockCityIdpCheck:
    provider: str
    ok: bool
    message: str
    fix: str
    auth_method: str | None = None
    subject: str | None = None
    roles: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "ok": self.ok,
            "message": self.message,
            "fix": self.fix,
            "auth_method": self.auth_method,
            "subject": self.subject,
            "roles": list(self.roles),
        }


@dataclass(frozen=True)
class MockCityBackupRetentionCheck:
    city: str
    ok: bool
    message: str
    fix: str
    checked_fields: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "ok": self.ok,
            "message": self.message,
            "fix": self.fix,
            "checked_fields": list(self.checked_fields),
        }


@dataclass(frozen=True)
class DemoTownFixtureContract:
    """Versioned, deterministic and independently authored municipal demo data."""

    schema_version: str
    fixture_id: str
    fixture_version: str
    deterministic_seed: str
    generated_at: str
    municipality: dict[str, Any]
    sources: tuple[dict[str, Any], ...]
    records: tuple[dict[str, Any], ...]
    requests: tuple[dict[str, Any], ...]
    expected: dict[str, Any]

    def public_dict(self) -> dict[str, Any]:
        sources = json.loads(json.dumps(self.sources))
        records = []
        for source_record in json.loads(json.dumps(self.records)):
            record = dict(source_record)
            record["content_sha256"] = _sha256_text(record["content"])
            records.append(record)
        requests = json.loads(json.dumps(self.requests))
        expected = json.loads(json.dumps(self.expected))
        artifact_hashes = {
            "sources.json": _sha256_json(sources),
            "records.json": _sha256_json(records),
            "requests.json": _sha256_json(requests),
            "expected.json": _sha256_json(expected),
        }
        payload = {
            "manifest": {
                "schema_version": self.schema_version,
                "fixture_id": self.fixture_id,
                "fixture_version": self.fixture_version,
                "deterministic_seed": self.deterministic_seed,
                "generation_mode": DEMO_TOWN_GENERATION_MODE,
                "generated_at": self.generated_at,
                "generator": "civiccore.testing.mock_city",
                "municipality": dict(self.municipality),
                "synthetic": True,
                "watermark": DEMO_TOWN_WATERMARK,
                "network_calls": False,
                "provenance_modes": list(DEMO_TOWN_PROVENANCE_MODES),
                "artifact_hashes": artifact_hashes,
            },
            "sources": sources,
            "records": records,
            "requests": requests,
            "expected": expected,
        }
        payload["fixture_sha256"] = _sha256_json(payload)
        return payload


def demo_town_fixture_contract() -> DemoTownFixtureContract:
    """Return the canonical v1 fictional-town records contract without I/O."""

    source_id = "townlight-independent-authorship-v1"
    request_id = "rv-request-2026-0001"
    return DemoTownFixtureContract(
        schema_version=DEMO_TOWN_CONTRACT_SCHEMA_VERSION,
        fixture_id=DEMO_TOWN_FIXTURE_ID,
        fixture_version=DEMO_TOWN_FIXTURE_VERSION,
        deterministic_seed=DEMO_TOWN_DEFAULT_SEED,
        generated_at=DEMO_TOWN_GENERATED_AT,
        municipality={
            "municipality_id": "redstone-valley-fictional",
            "name": DEMO_TOWN_NAME,
            "state": "CO",
            "timezone": "America/Denver",
            "population_band": "50,000-100,000",
            "fictional": True,
        },
        sources=(
            {
                "source_id": source_id,
                "publisher": "Townlight fixture authors",
                "canonical_url": None,
                "retrieved_at": None,
                "content": (
                    "Independent authorship source for Redstone Valley fixture version 1.0.0"
                ),
                "content_sha256": _sha256_text(
                    "Independent authorship source for Redstone Valley fixture version 1.0.0"
                ),
                "acquisition_method": "independent-authorship",
                "provenance_mode": "fully-synthetic",
                "license_or_permission": "Apache-2.0",
                "allowed_uses": ["testing", "demonstration", "redistribution"],
                "redistributable": True,
                "contains_personal_data": False,
                "notes": (
                    "Project-authored fictional content that is not copied or adapted "
                    "from any real municipality or media organization."
                ),
            },
        ),
        records=(
            {
                "record_id": "rv-record-council-0001",
                "title": "Council action summary for the demonstration calendar",
                "department": "Town Clerk",
                "record_type": "meeting-summary",
                "created_at": "2026-08-04T20:00:00Z",
                "retention_class": "fictional-permanent",
                "access_class": "public",
                "source_refs": [source_id],
                "derivation": "independently-authored",
                "synthetic": True,
                "watermark": DEMO_TOWN_WATERMARK,
                "contains_personal_data": False,
                "content": (
                    "The fictional council accepted the prior action summary and approved "
                    "a demonstration-only trail maintenance schedule. No real vote, person, "
                    "place, ordinance, or meeting is represented."
                ),
                "ground_truth_tags": ["council", "trail-maintenance", "public"],
            },
            {
                "record_id": "rv-record-trails-0001",
                "title": "Demonstration trail inspection summary",
                "department": "Parks and Open Space",
                "record_type": "inspection-summary",
                "created_at": "2026-08-05T15:30:00Z",
                "retention_class": "fictional-operational",
                "access_class": "public",
                "source_refs": [source_id],
                "derivation": "independently-authored",
                "synthetic": True,
                "watermark": DEMO_TOWN_WATERMARK,
                "contains_personal_data": False,
                "content": (
                    "A synthetic inspection found two demonstration markers needing "
                    "replacement and one invented drainage segment scheduled for review."
                ),
                "ground_truth_tags": ["parks", "inspection", "trail-maintenance"],
            },
            {
                "record_id": "rv-record-water-0001",
                "title": "Synthetic utility sampling summary",
                "department": "Utilities",
                "record_type": "sampling-summary",
                "created_at": "2026-08-06T14:15:00Z",
                "retention_class": "fictional-operational",
                "access_class": "public",
                "source_refs": [source_id],
                "derivation": "independently-authored",
                "synthetic": True,
                "watermark": DEMO_TOWN_WATERMARK,
                "contains_personal_data": False,
                "content": (
                    "All invented samples in this software fixture matched its fictional "
                    "test thresholds. This statement is not regulatory or safety guidance."
                ),
                "ground_truth_tags": ["utilities", "sampling", "public"],
            },
        ),
        requests=(
            {
                "request_id": request_id,
                "requester_category": "synthetic-public-requester",
                "description": (
                    "Provide the fictional trail maintenance schedule and its related "
                    "demonstration inspection summary."
                ),
                "received_at": "2026-08-17T16:00:00Z",
                "target_record_ids": [
                    "rv-record-council-0001",
                    "rv-record-trails-0001",
                ],
                "policy_basis": "fictional-demo-policy-v1",
                "synthetic": True,
                "watermark": DEMO_TOWN_WATERMARK,
                "contains_personal_data": False,
            },
        ),
        expected={
            "search": [
                {
                    "query": "trail maintenance schedule",
                    "record_ids": [
                        "rv-record-council-0001",
                        "rv-record-trails-0001",
                    ],
                },
                {
                    "query": "utility sampling",
                    "record_ids": ["rv-record-water-0001"],
                },
            ],
            "pii": {
                "expected_findings": [],
                "record_ids": [
                    "rv-record-council-0001",
                    "rv-record-trails-0001",
                    "rv-record-water-0001",
                ],
            },
            "workflow": {
                "request_id": request_id,
                "status_sequence": [*DEMO_TOWN_WORKFLOW_STATUSES],
                "human_approval_required": True,
            },
            "counts": {"sources": 1, "records": 3, "requests": 1},
        },
    )


def demo_town_fixture() -> dict[str, Any]:
    """Build the canonical v1 public fixture and verify its safety contract."""

    fixture = demo_town_fixture_contract().public_dict()
    assert_demo_town_fixture_safe(fixture)
    return fixture


def _closed_object_errors(
    value: dict[str, Any], expected_fields: set[str], context: str
) -> list[str]:
    errors = [
        f"{context}.{field_name} is required"
        for field_name in sorted(expected_fields - set(value))
    ]
    errors.extend(
        f"{context}.{field_name} is not allowed"
        for field_name in sorted(set(value) - expected_fields)
    )
    return errors


def _reference_list_errors(
    value: Any,
    valid_ids: set[str],
    context: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        return [f"{context} must be a list"]
    errors: list[str] = []
    if not value and not allow_empty:
        errors.append(f"{context} must not be empty")
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            errors.append(f"{context} contains a non-string reference")
            continue
        if item in seen:
            errors.append(f"{context} contains duplicate reference {item!r}")
        seen.add(item)
        if item not in valid_ids:
            errors.append(f"{context} contains unknown reference {item!r}")
    return errors


def validate_demo_town_fixture(fixture: dict[str, Any]) -> tuple[str, ...]:
    """Return deterministic contract errors for a candidate demo-town fixture."""

    errors: list[str] = []
    root_fields = {"manifest", "sources", "records", "requests", "expected", "fixture_sha256"}
    errors.extend(_closed_object_errors(fixture, root_fields, "fixture"))
    manifest = fixture.get("manifest")
    if not isinstance(manifest, dict):
        return ("manifest must be an object",)

    manifest_fields = {
        "schema_version",
        "fixture_id",
        "fixture_version",
        "deterministic_seed",
        "generation_mode",
        "generated_at",
        "generator",
        "municipality",
        "synthetic",
        "watermark",
        "network_calls",
        "provenance_modes",
        "artifact_hashes",
    }
    errors.extend(_closed_object_errors(manifest, manifest_fields, "manifest"))
    expected_manifest_values = {
        "schema_version": DEMO_TOWN_CONTRACT_SCHEMA_VERSION,
        "fixture_id": DEMO_TOWN_FIXTURE_ID,
        "fixture_version": DEMO_TOWN_FIXTURE_VERSION,
        "deterministic_seed": DEMO_TOWN_DEFAULT_SEED,
        "generation_mode": DEMO_TOWN_GENERATION_MODE,
        "generated_at": DEMO_TOWN_GENERATED_AT,
        "generator": "civiccore.testing.mock_city",
        "synthetic": True,
        "watermark": DEMO_TOWN_WATERMARK,
        "network_calls": False,
    }
    for field_name, expected_value in expected_manifest_values.items():
        if manifest.get(field_name) != expected_value:
            errors.append(f"manifest.{field_name} must equal {expected_value!r}")

    municipality = manifest.get("municipality")
    expected_municipality = {
        "municipality_id": "redstone-valley-fictional",
        "name": DEMO_TOWN_NAME,
        "state": "CO",
        "timezone": "America/Denver",
        "population_band": "50,000-100,000",
        "fictional": True,
    }
    if not isinstance(municipality, dict):
        errors.append("manifest.municipality must be an object")
    elif municipality != expected_municipality:
        errors.append("manifest.municipality must equal the canonical fictional municipality")

    if manifest.get("provenance_modes") != list(DEMO_TOWN_PROVENANCE_MODES):
        errors.append("manifest.provenance_modes must contain only fully-synthetic for v1")

    sources = fixture.get("sources")
    records = fixture.get("records")
    requests = fixture.get("requests")
    expected = fixture.get("expected")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        sources = []
    if not isinstance(records, list):
        errors.append("records must be a list")
        records = []
    if not isinstance(requests, list):
        errors.append("requests must be a list")
        requests = []
    if not isinstance(expected, dict):
        errors.append("expected must be an object")
        expected = {}

    source_ids: set[str] = set()
    source_fields = {
        "source_id",
        "publisher",
        "canonical_url",
        "retrieved_at",
        "content",
        "content_sha256",
        "acquisition_method",
        "provenance_mode",
        "license_or_permission",
        "allowed_uses",
        "redistributable",
        "contains_personal_data",
        "notes",
    }
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_closed_object_errors(source, source_fields, prefix))
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not _DEMO_TOWN_ID_RE.fullmatch(source_id):
            errors.append(f"{prefix}.source_id must be a stable identifier")
        elif source_id in source_ids:
            errors.append(f"{prefix}.source_id duplicates {source_id!r}")
        else:
            source_ids.add(source_id)
        if source.get("provenance_mode") != "fully-synthetic":
            errors.append(f"{prefix}.provenance_mode must be 'fully-synthetic' in v1")
        if source.get("acquisition_method") != "independent-authorship":
            errors.append(f"{prefix}.acquisition_method must be independent-authorship")
        if source.get("contains_personal_data") is not False:
            errors.append(f"{prefix} must declare contains_personal_data false")
        if source.get("redistributable") is not True:
            errors.append(f"{prefix} must be redistributable")
        if source.get("canonical_url") is not None:
            errors.append(f"{prefix}.canonical_url must be null for fully synthetic content")
        if source.get("retrieved_at") is not None:
            errors.append(f"{prefix}.retrieved_at must be null for independently authored content")
        if not isinstance(source.get("license_or_permission"), str) or not source.get(
            "license_or_permission"
        ):
            errors.append(f"{prefix}.license_or_permission must be explicit")
        if source.get("allowed_uses") != ["testing", "demonstration", "redistribution"]:
            errors.append(f"{prefix}.allowed_uses must authorize the canonical public fixture uses")
        content = source.get("content")
        if not isinstance(content, str) or not content:
            errors.append(f"{prefix}.content must materialize the independently authored source")
        elif source.get("content_sha256") != _sha256_text(content):
            errors.append(f"{prefix}.content_sha256 does not match content")

    record_ids: set[str] = set()
    record_fields = {
        "record_id",
        "title",
        "department",
        "record_type",
        "created_at",
        "retention_class",
        "access_class",
        "source_refs",
        "derivation",
        "synthetic",
        "watermark",
        "contains_personal_data",
        "content",
        "content_sha256",
        "ground_truth_tags",
    }
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_closed_object_errors(record, record_fields, prefix))
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not _DEMO_TOWN_ID_RE.fullmatch(record_id):
            errors.append(f"{prefix}.record_id must be a stable identifier")
        elif record_id in record_ids:
            errors.append(f"{prefix}.record_id duplicates {record_id!r}")
        else:
            record_ids.add(record_id)
        errors.extend(
            _reference_list_errors(record.get("source_refs"), source_ids, f"{prefix}.source_refs")
        )
        if record.get("synthetic") is not True:
            errors.append(f"{prefix} must be explicitly synthetic")
        if record.get("watermark") != DEMO_TOWN_WATERMARK:
            errors.append(f"{prefix} must carry the canonical synthetic watermark")
        if record.get("contains_personal_data") is not False:
            errors.append(f"{prefix} must declare contains_personal_data false")
        content = record.get("content")
        if not isinstance(content, str) or not content:
            errors.append(f"{prefix}.content must be non-empty text")
        elif record.get("content_sha256") != _sha256_text(content):
            errors.append(f"{prefix}.content_sha256 does not match content")

    request_ids: set[str] = set()
    request_fields = {
        "request_id",
        "requester_category",
        "description",
        "received_at",
        "target_record_ids",
        "policy_basis",
        "synthetic",
        "watermark",
        "contains_personal_data",
    }
    for index, request in enumerate(requests):
        prefix = f"requests[{index}]"
        if not isinstance(request, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_closed_object_errors(request, request_fields, prefix))
        request_id = request.get("request_id")
        if not isinstance(request_id, str) or not _DEMO_TOWN_ID_RE.fullmatch(request_id):
            errors.append(f"{prefix}.request_id must be a stable identifier")
        elif request_id in request_ids:
            errors.append(f"{prefix}.request_id duplicates {request_id!r}")
        else:
            request_ids.add(request_id)
        errors.extend(
            _reference_list_errors(
                request.get("target_record_ids"), record_ids, f"{prefix}.target_record_ids"
            )
        )
        if request.get("synthetic") is not True:
            errors.append(f"{prefix} must be explicitly synthetic")
        if request.get("watermark") != DEMO_TOWN_WATERMARK:
            errors.append(f"{prefix} must carry the canonical synthetic watermark")
        if request.get("contains_personal_data") is not False:
            errors.append(f"{prefix} must declare contains_personal_data false")

    expected_fields = {"search", "pii", "workflow", "counts"}
    errors.extend(_closed_object_errors(expected, expected_fields, "expected"))
    searches = expected.get("search")
    if not isinstance(searches, list):
        errors.append("expected.search must be a list")
    else:
        seen_queries: set[str] = set()
        for index, search in enumerate(searches):
            prefix = f"expected.search[{index}]"
            if not isinstance(search, dict):
                errors.append(f"{prefix} must be an object")
                continue
            errors.extend(_closed_object_errors(search, {"query", "record_ids"}, prefix))
            query = search.get("query")
            if not isinstance(query, str) or not query.strip():
                errors.append(f"{prefix}.query must be non-empty")
            elif query in seen_queries:
                errors.append(f"{prefix}.query duplicates {query!r}")
            else:
                seen_queries.add(query)
            errors.extend(
                _reference_list_errors(search.get("record_ids"), record_ids, f"{prefix}.record_ids")
            )

    pii = expected.get("pii")
    if not isinstance(pii, dict):
        errors.append("expected.pii must be an object")
    else:
        errors.extend(
            _closed_object_errors(pii, {"expected_findings", "record_ids"}, "expected.pii")
        )
        if pii.get("expected_findings") != []:
            errors.append("expected.pii.expected_findings must be empty for the v1 fixture")
        errors.extend(
            _reference_list_errors(pii.get("record_ids"), record_ids, "expected.pii.record_ids")
        )
        if (
            isinstance(pii.get("record_ids"), list)
            and all(isinstance(item, str) for item in pii["record_ids"])
            and set(pii["record_ids"]) != record_ids
        ):
            errors.append("expected.pii.record_ids must cover every fixture record")

    workflow = expected.get("workflow")
    if not isinstance(workflow, dict):
        errors.append("expected.workflow must be an object")
    else:
        errors.extend(
            _closed_object_errors(
                workflow,
                {"request_id", "status_sequence", "human_approval_required"},
                "expected.workflow",
            )
        )
        if workflow.get("request_id") not in request_ids:
            errors.append("expected.workflow.request_id must reference a fixture request")
        if workflow.get("status_sequence") != list(DEMO_TOWN_WORKFLOW_STATUSES):
            errors.append("expected.workflow.status_sequence must equal the canonical sequence")
        if workflow.get("human_approval_required") is not True:
            errors.append("expected.workflow.human_approval_required must be true")

    counts = expected.get("counts")
    expected_counts = {"sources": len(sources), "records": len(records), "requests": len(requests)}
    if counts != expected_counts:
        errors.append(f"expected.counts must equal {expected_counts!r}")

    expected_artifact_hashes = {
        "sources.json": _sha256_json(sources),
        "records.json": _sha256_json(records),
        "requests.json": _sha256_json(requests),
        "expected.json": _sha256_json(expected),
    }
    if manifest.get("artifact_hashes") != expected_artifact_hashes:
        errors.append("manifest.artifact_hashes do not match fixture artifacts")

    fixture_without_hash = dict(fixture)
    fixture_without_hash.pop("fixture_sha256", None)
    if fixture.get("fixture_sha256") != _sha256_json(fixture_without_hash):
        errors.append("fixture_sha256 does not match fixture content")
    if fixture.get("fixture_sha256") != DEMO_TOWN_FIXTURE_SHA256_V1:
        errors.append("fixture_sha256 does not match the pinned v1 golden fixture")
    return tuple(errors)


def assert_demo_town_fixture_safe(fixture: dict[str, Any]) -> None:
    """Apply conservative privacy heuristics and the closed public fixture contract.

    These checks reduce accidental disclosure risk; they do not claim to identify
    every possible person name or item of personal data in arbitrary free text.
    """

    forbidden_fields = sorted(
        field_name
        for field_name in _nested_field_names(fixture)
        if _is_forbidden_personal_field(field_name)
    )
    if forbidden_fields:
        raise ValueError(
            "demo town fixture contains forbidden personal-data fields: "
            + ", ".join(forbidden_fields)
        )

    serialized = json.dumps(fixture, sort_keys=True, ensure_ascii=False)
    pii_matches = sorted(
        name for name, pattern in _DEMO_TOWN_PII_PATTERNS.items() if pattern.search(serialized)
    )
    if pii_matches:
        raise ValueError(
            "demo town fixture contains forbidden PII patterns: " + ", ".join(pii_matches)
        )

    assert_secret_free_report(fixture)
    errors = validate_demo_town_fixture(fixture)
    if errors:
        raise ValueError("invalid demo town fixture: " + "; ".join(errors))


def _is_forbidden_personal_field(field_name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", field_name.lower()).strip("_")
    return normalized in _DEMO_TOWN_FORBIDDEN_PERSONAL_FIELDS or bool(
        _DEMO_TOWN_PERSONAL_NAME_FIELD_RE.fullmatch(normalized)
    )


def _nested_field_names(value: Any) -> list[str]:
    names: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            names.append(str(key))
            names.extend(_nested_field_names(child))
    elif isinstance(value, list | tuple):
        for child in value:
            names.extend(_nested_field_names(child))
    return names


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def mock_city_vendor_contracts() -> list[MockCityVendorContract]:
    """Return reusable vendor contracts for mock-city integration tests."""

    return [
        MockCityVendorContract(
            connector="legistar",
            vendor_name="Legistar",
            interface_status="public-reference",
            method="GET",
            path="/v1/{Client}/Events?EventItems=true",
            auth_method="bearer_token",
            delta_query_param="LastModifiedDate",
            sample_payload={
                "MeetingId": "leg-brookfield-100",
                "MeetingName": "Brookfield City Council Regular Meeting",
                "MeetingDate": "2026-05-06T18:30:00Z",
                "AgendaItems": [
                    {"FileNumber": "24-001", "Title": "Approve minutes", "DepartmentName": "Clerk"},
                    {
                        "FileNumber": "24-002",
                        "Title": "Adopt sidewalk repair resolution",
                        "DepartmentName": "Public Works",
                    },
                ],
            },
            notes=(
                "Legistar exposes a public Web API help surface with Events routes. "
                "Tenant-specific client names and credentials still come from the city/vendor account."
            ),
        ),
        MockCityVendorContract(
            connector="granicus",
            vendor_name="Granicus",
            interface_status="vendor-gated-contract",
            method="GET",
            path="/api/meetings",
            auth_method="api_key",
            delta_query_param="modifiedSince",
            sample_payload={
                "id": "gr-brookfield-100",
                "name": "Brookfield City Council Work Session",
                "start": "2026-05-07T19:00:00Z",
                "agenda": [
                    {"id": "gr-item-1", "title": "Review capital plan", "department": "Finance"},
                ],
            },
            notes=(
                "Public marketing confirms Granicus meeting-management products, but customer API details are account-gated. "
                "This fixture tests CivicSuite's normalized contract until city credentials provide a concrete endpoint."
            ),
        ),
        MockCityVendorContract(
            connector="primegov",
            vendor_name="PrimeGov",
            interface_status="vendor-gated-contract",
            method="GET",
            path="/api/meetings",
            auth_method="bearer_token",
            delta_query_param="updated_since",
            sample_payload={
                "meeting_id": "pg-brookfield-100",
                "title": "Planning Commission",
                "scheduled_start": "2026-05-08T01:00:00Z",
                "items": [
                    {"item_id": "pg-item-1", "subject": "Conditional use permit", "owner": "Planning"},
                ],
            },
            notes="PrimeGov tenant APIs are treated as vendor-gated until a city provides interface documentation.",
        ),
        MockCityVendorContract(
            connector="novusagenda",
            vendor_name="NovusAGENDA",
            interface_status="vendor-gated-contract",
            method="GET",
            path="/api/meetings",
            auth_method="api_key",
            delta_query_param="modifiedSince",
            sample_payload={
                "MeetingGuid": "nov-brookfield-100",
                "MeetingTitle": "Parks Board",
                "MeetingDateTime": "2026-05-09T17:00:00Z",
                "Agenda": [
                    {"Guid": "nov-item-1", "Caption": "Trail maintenance grant", "Dept": "Parks"},
                ],
            },
            notes="NovusAGENDA tenant APIs are treated as vendor-gated until a city provides interface documentation.",
        ),
    ]


def mock_city_idp_contract() -> MockCityIdpContract:
    """Return the reusable no-network municipal IdP contract for protected staff auth."""

    return MockCityIdpContract(
        provider="Brookfield Entra ID",
        interface_status="mock-municipal-idp",
        issuer="https://login.mock-city.example.gov/brookfield/v2.0",
        audience="api://civicsuite-staff",
        authorization_url="https://login.mock-city.example.gov/brookfield/oauth2/v2.0/authorize",
        token_url="https://login.mock-city.example.gov/brookfield/oauth2/v2.0/token",
        jwks_path="/brookfield/discovery/v2.0/keys",
        role_claims=("roles", "groups"),
        algorithms=("RS256",),
        client_id="civicsuite-staff-dashboard",
        redirect_uri="https://module.mock-city.example.gov/staff/oidc/callback",
        staff_subject="brookfield-clerk-001",
        staff_email="clerk@brookfield.example.gov",
        staff_roles=("clerk_admin", "meeting_editor"),
        notes=(
            "Models the authorization-code + PKCE and JWKS/token contract CivicSuite modules "
            "must satisfy before replacing mock evidence with a real municipal tenant."
        ),
    )


def mock_city_backup_retention_contract() -> MockCityBackupRetentionContract:
    """Return the reusable no-network backup retention/off-host evidence contract."""

    return MockCityBackupRetentionContract(
        city=MOCK_CITY_NAME,
        interface_status="mock-policy-contract",
        backup_scope=(
            "postgresql_application_tables",
            "export_bundles",
            "connector_import_ledgers",
            "vendor_sync_reports",
            "release_handoff_artifacts",
        ),
        restore_proof_required=True,
        manifest_required_fields=(
            "service",
            "created_at",
            "source",
            "dump.sha256",
            "dump.size",
            "verification",
            "restored_application_tables",
        ),
        retention_years=7,
        restore_test_interval_days=30,
        off_host_storage="mock://brookfield-secure-vault/civicsuite",
        encryption_at_rest_required=True,
        immutable_retention_required=True,
        legal_hold_supported=True,
        approval_artifact="mock-brookfield-backup-retention-policy-2026-05",
        notes=(
            "Models the policy evidence CivicSuite modules must provide before replacing "
            "mock proof with a city-approved retention schedule and off-host storage runbook."
        ),
    )


def run_mock_city_contract_suite(*, base_url: str = "https://mock-city.example.gov") -> list[MockCityContractCheck]:
    """Validate mock city payloads and delta URLs without contacting vendors."""

    checks: list[MockCityContractCheck] = []
    for contract in mock_city_vendor_contracts():
        if contract.connector not in SUPPORTED_CONNECTORS:
            checks.append(
                MockCityContractCheck(
                    connector=contract.connector,
                    ok=False,
                    message=f"{contract.vendor_name} is not on the shared connector allowlist.",
                    fix="Add the connector to Townlight Core before adding module-level mock-city tests.",
                )
            )
            continue
        if contract.interface_status not in MOCK_CITY_INTERFACE_STATUS:
            checks.append(
                MockCityContractCheck(
                    connector=contract.connector,
                    ok=False,
                    message=f"{contract.vendor_name} has an unknown interface status.",
                    fix="Use public-reference or vendor-gated-contract so test evidence stays honest.",
                )
            )
            continue
        try:
            normalized = import_meeting_payload(
                connector_name=contract.connector,
                payload=contract.sample_payload,
            ).public_dict()
            delta_plan = plan_vendor_delta_request(
                connector=contract.connector,
                source_url=f"{base_url}{contract.path.replace('{Client}', 'brookfield')}",
                changed_since=MOCK_CITY_CHANGED_SINCE,
            )
        except Exception as exc:  # pragma: no cover - defensive safety net for CLI output.
            checks.append(
                MockCityContractCheck(
                    connector=contract.connector,
                    ok=False,
                    message=f"{contract.vendor_name} mock city contract failed: {exc}",
                    fix="Update the mock payload or connector adapter before reusing this suite.",
                )
            )
            continue
        checks.append(
            MockCityContractCheck(
                connector=contract.connector,
                ok=True,
                message=(
                    f"{contract.vendor_name} mock city contract normalized "
                    f"{normalized['external_meeting_id']} and planned a delta request."
                ),
                fix="Reuse this contract in module integration tests; replace only the module-specific assertions.",
                normalized_external_meeting_id=normalized["external_meeting_id"],
                delta_request_url=delta_plan.request_url,
            )
        )
    return checks


def run_mock_city_idp_contract_suite() -> list[MockCityIdpCheck]:
    """Validate the mock municipal IdP contract without contacting an IdP."""

    contract = mock_city_idp_contract()
    try:
        token = _mock_city_staff_token(contract)
        public_key = _mock_city_private_key().public_key()
        claims = jwt.decode(
            token,
            public_key,
            algorithms=list(contract.algorithms),
            audience=contract.audience,
            issuer=contract.issuer,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI reporting.
        return [
            MockCityIdpCheck(
                provider=contract.provider,
                ok=False,
                message=f"Mock municipal IdP token validation failed: {exc}",
                fix="Align issuer, audience, JWKS, role claims, and allowed staff roles before reuse.",
            )
        ]

    roles = tuple(sorted(role for claim in contract.role_claims for role in claims.get(claim, [])))
    if not set(roles).intersection(MOCK_CITY_STAFF_ROLES):
        return [
            MockCityIdpCheck(
                provider=contract.provider,
                ok=False,
                message="Mock municipal IdP token did not contain any allowed staff role.",
                fix="Include at least one allowed Townlight staff role in the mock IdP contract.",
            )
        ]

    return [
        MockCityIdpCheck(
            provider=contract.provider,
            ok=True,
            message=f"{contract.provider} mock OIDC contract validated {contract.staff_email} with staff roles.",
            fix="Reuse this IdP contract in module protected-auth tests; replace only module-specific staff actions.",
            auth_method="oidc",
            subject=contract.staff_email,
            roles=roles,
        )
    ]


def run_mock_city_backup_retention_suite() -> list[MockCityBackupRetentionCheck]:
    """Validate the mock backup-retention contract without contacting storage providers."""

    contract = mock_city_backup_retention_contract()
    checks: list[MockCityBackupRetentionCheck] = []
    missing_fields = [
        field
        for field in contract.manifest_required_fields
        if not field or field.strip() != field
    ]
    missing_scope = [scope for scope in contract.backup_scope if not scope or scope.strip() != scope]
    if missing_fields or missing_scope:
        checks.append(
            MockCityBackupRetentionCheck(
                city=contract.city,
                ok=False,
                message="Mock backup retention contract has blank or malformed manifest/scope fields.",
                fix="Use stable manifest field names and backup scope labels before reusing the contract.",
            )
        )
    if contract.retention_years < 7:
        checks.append(
            MockCityBackupRetentionCheck(
                city=contract.city,
                ok=False,
                message="Mock backup retention contract is shorter than the Brookfield seven-year record baseline.",
                fix="Set retention_years to at least 7 or document the jurisdiction-specific exception.",
            )
        )
    if contract.restore_test_interval_days > 30:
        checks.append(
            MockCityBackupRetentionCheck(
                city=contract.city,
                ok=False,
                message="Mock backup retention contract allows restore tests less often than monthly.",
                fix="Set restore_test_interval_days to 30 or less for reusable module readiness proof.",
            )
        )
    if not contract.off_host_storage.startswith("mock://"):
        checks.append(
            MockCityBackupRetentionCheck(
                city=contract.city,
                ok=False,
                message="Mock backup retention contract must use a non-network mock:// off-host destination.",
                fix="Use a mock:// destination until a real city storage proof artifact is attached.",
            )
        )
    if not (
        contract.restore_proof_required
        and contract.encryption_at_rest_required
        and contract.immutable_retention_required
        and contract.legal_hold_supported
    ):
        checks.append(
            MockCityBackupRetentionCheck(
                city=contract.city,
                ok=False,
                message="Mock backup retention contract is missing restore, encryption, immutability, or legal-hold proof.",
                fix="Require restore proof, encrypted storage, immutable retention, and legal-hold support.",
            )
        )
    if checks:
        return checks
    return [
        MockCityBackupRetentionCheck(
            city=contract.city,
            ok=True,
            message=(
                f"{contract.city} mock backup-retention contract covers restore proof, "
                "seven-year retention, monthly restore tests, encrypted immutable off-host storage, and legal hold."
            ),
            fix="Reuse this contract in module backup-readiness tests; replace only the real city proof artifact.",
            checked_fields=contract.manifest_required_fields,
        )
    ]


def _mock_city_staff_token(contract: MockCityIdpContract) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": contract.issuer,
            "aud": contract.audience,
            "sub": contract.staff_subject,
            "preferred_username": contract.staff_email,
            "roles": list(contract.staff_roles),
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        _mock_city_private_key(),
        algorithm="RS256",
        headers={"kid": MOCK_CITY_IDP_KEY_ID},
    )


@lru_cache(maxsize=1)
def _mock_city_private_key() -> rsa.RSAPrivateKey:
    """Generate one in-memory keypair per process for offline IdP contract validation."""

    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def mock_city_report() -> dict[str, Any]:
    """Return a secret-free JSON-ready report for module readiness tooling."""

    return {
        "mock_city": MOCK_CITY_NAME,
        "network_calls": False,
        "ready": True,
        "contracts": [contract.public_dict() for contract in mock_city_vendor_contracts()],
        "checks": [check.public_dict() for check in run_mock_city_contract_suite()],
        "idp_contract": mock_city_idp_contract().public_dict(),
        "idp_checks": [check.public_dict() for check in run_mock_city_idp_contract_suite()],
        "backup_retention_contract": mock_city_backup_retention_contract().public_dict(),
        "backup_retention_checks": [
            check.public_dict() for check in run_mock_city_backup_retention_suite()
        ],
    }


def assert_secret_free_report(report: dict[str, Any]) -> None:
    """Raise ValueError if a mock city report appears to expose credential values."""

    serialized = json.dumps(report).lower()
    forbidden = ("password", "secret", "token_value", "api_key_value")
    leaked = [term for term in forbidden if term in serialized]
    if leaked:
        raise ValueError(f"mock city report contains forbidden secret terms: {', '.join(leaked)}")


__all__ = [
    "DEMO_TOWN_CONTRACT_SCHEMA_VERSION",
    "DEMO_TOWN_DEFAULT_SEED",
    "DEMO_TOWN_FIXTURE_ID",
    "DEMO_TOWN_FIXTURE_SHA256_V1",
    "DEMO_TOWN_FIXTURE_VERSION",
    "DEMO_TOWN_GENERATION_MODE",
    "DEMO_TOWN_NAME",
    "DEMO_TOWN_PROVENANCE_MODES",
    "DEMO_TOWN_WATERMARK",
    "MOCK_CITY_CHANGED_SINCE",
    "MOCK_CITY_NAME",
    "MOCK_CITY_STAFF_ROLES",
    "DemoTownFixtureContract",
    "MockCityBackupRetentionCheck",
    "MockCityBackupRetentionContract",
    "MockCityContractCheck",
    "MockCityIdpCheck",
    "MockCityIdpContract",
    "MockCityVendorContract",
    "assert_demo_town_fixture_safe",
    "assert_secret_free_report",
    "demo_town_fixture",
    "demo_town_fixture_contract",
    "mock_city_backup_retention_contract",
    "mock_city_idp_contract",
    "mock_city_report",
    "mock_city_vendor_contracts",
    "run_mock_city_backup_retention_suite",
    "run_mock_city_contract_suite",
    "run_mock_city_idp_contract_suite",
    "validate_demo_town_fixture",
]
