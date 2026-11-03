from __future__ import annotations

import json

from townlight_core.testing import (
    MOCK_CITY_NAME,
    assert_secret_free_report,
    mock_city_backup_retention_contract,
    mock_city_idp_contract,
    mock_city_report,
    mock_city_vendor_contracts,
    run_mock_city_backup_retention_suite,
    run_mock_city_contract_suite,
    run_mock_city_idp_contract_suite,
)


def test_mock_city_contracts_cover_supported_agenda_vendor_interfaces() -> None:
    contracts = {contract.connector: contract for contract in mock_city_vendor_contracts()}

    assert set(contracts) == {"granicus", "legistar", "novusagenda", "primegov"}
    assert MOCK_CITY_NAME == "City of Brookfield"
    assert contracts["legistar"].interface_status == "public-reference"
    assert contracts["legistar"].path == "/v1/{Client}/Events?EventItems=true"
    assert contracts["legistar"].delta_query_param == "LastModifiedDate"
    assert contracts["granicus"].interface_status == "vendor-gated-contract"
    assert contracts["primegov"].delta_query_param == "updated_since"
    assert contracts["novusagenda"].delta_query_param == "modifiedSince"


def test_mock_city_suite_normalizes_payloads_and_plans_delta_urls() -> None:
    checks = run_mock_city_contract_suite(base_url="https://mock-city.example.gov")

    assert len(checks) == 4
    assert all(check.ok for check in checks)
    by_connector = {check.connector: check for check in checks}
    assert by_connector["legistar"].normalized_external_meeting_id == "leg-brookfield-100"
    assert "LastModifiedDate=2026-05-01T12%3A00%3A00Z" in by_connector["legistar"].delta_request_url
    assert "modifiedSince=2026-05-01T12%3A00%3A00Z" in by_connector["granicus"].delta_request_url
    assert "updated_since=2026-05-01T12%3A00%3A00Z" in by_connector["primegov"].delta_request_url
    assert "network" not in " ".join(check.message.lower() for check in checks)


def test_mock_city_idp_contract_validates_staff_oidc_without_network() -> None:
    contract = mock_city_idp_contract()
    checks = run_mock_city_idp_contract_suite()

    assert contract.provider == "Brookfield Entra ID"
    assert contract.interface_status == "mock-municipal-idp"
    assert contract.jwks_path.endswith("/keys")
    assert contract.role_claims == ("roles", "groups")
    assert contract.algorithms == ("RS256",)
    assert len(checks) == 1
    assert checks[0].ok is True
    assert checks[0].auth_method == "oidc"
    assert checks[0].subject == "clerk@brookfield.example.gov"
    assert checks[0].roles == ("clerk_admin", "meeting_editor")


def test_mock_city_backup_retention_contract_validates_policy_without_network() -> None:
    contract = mock_city_backup_retention_contract()
    checks = run_mock_city_backup_retention_suite()

    assert contract.city == MOCK_CITY_NAME
    assert contract.interface_status == "mock-policy-contract"
    assert contract.retention_years >= 7
    assert contract.restore_test_interval_days <= 30
    assert contract.off_host_storage.startswith("mock://")
    assert contract.restore_proof_required is True
    assert contract.encryption_at_rest_required is True
    assert contract.immutable_retention_required is True
    assert contract.legal_hold_supported is True
    assert "dump.sha256" in contract.manifest_required_fields
    assert len(checks) == 1
    assert checks[0].ok is True
    assert "seven-year retention" in checks[0].message


def test_mock_city_report_is_public_and_secret_free() -> None:
    report = mock_city_report()

    assert report["mock_city"] == "City of Brookfield"
    assert report["network_calls"] is False
    assert report["ready"] is True
    assert {contract["connector"] for contract in report["contracts"]} == {
        "granicus",
        "legistar",
        "novusagenda",
        "primegov",
    }
    assert report["idp_checks"][0]["ok"] is True
    assert report["backup_retention_checks"][0]["ok"] is True
    assert_secret_free_report(report)
    serialized = json.dumps(report).lower()
    assert "tenant-specific" in serialized
