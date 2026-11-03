from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from townlight_core.city_profile import (
    CityProfile,
    DeploymentProfile,
    ModuleEnablement,
    load_city_profile,
)


def write_profile(tmp_path, payload: dict) -> str:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def valid_payload() -> dict:
    return {
        "city_name": "Sampleville",
        "timezone": "America/Denver",
        "departments": [
            {
                "name": "City Clerk",
                "slug": "city-clerk",
                "public_email": "clerk@example.gov",
            }
        ],
        "enabled_modules": [
            {"name": "records", "enabled": True},
            {"name": "permits", "enabled": False, "settings": {"pilot": True}},
        ],
        "default_llm_provider": "ollama",
        "file_drop_roots": ["C:/townlight_core/dropbox"],
        "public_contact": {
            "email": "info@example.gov",
            "phone": "555-0100",
        },
        "deployment": {"mode": "local_demo"},
    }


def test_load_valid_json_profile(tmp_path):
    profile = load_city_profile(write_profile(tmp_path, valid_payload()))

    assert profile.city_name == "Sampleville"
    assert profile.timezone == "America/Denver"
    assert profile.departments[0].slug == "city-clerk"
    assert profile.file_drop_roots[0].as_posix().endswith("townlight_core/dropbox")
    assert profile.public_contact["email"] == "info@example.gov"


def test_default_llm_provider_is_local_first():
    profile = CityProfile(city_name="Sampleville", timezone="America/Denver")

    assert profile.default_llm_provider == "ollama"
    assert profile.deployment.mode == "local_demo"
    assert profile.deployment.allow_outbound_services is False


def test_rejects_outbound_default_llm_provider_unless_explicitly_allowed():
    with pytest.raises(ValidationError, match="requires outbound services"):
        CityProfile(
            city_name="Sampleville",
            timezone="America/Denver",
            default_llm_provider="openai",
        )

    profile = CityProfile(
        city_name="Sampleville",
        timezone="America/Denver",
        default_llm_provider="openai",
        deployment=DeploymentProfile(mode="self_hosted", allow_outbound_services=True),
    )

    assert profile.default_llm_provider == "openai"


def test_requires_valid_timezone():
    with pytest.raises(ValidationError, match="timezone"):
        CityProfile(city_name="Sampleville", timezone="")

    with pytest.raises(ValidationError, match="valid IANA timezone"):
        CityProfile(city_name="Sampleville", timezone="Mountain Time")


def test_module_enablement_validates_names_and_enabled_flags():
    module = ModuleEnablement(name="records_ai", enabled=False, settings={"queue": "local"})

    assert module.name == "records_ai"
    assert module.enabled is False
    assert module.settings == {"queue": "local"}

    with pytest.raises(ValidationError):
        ModuleEnablement(name="Records AI", enabled=True)


def test_rejects_outbound_file_drop_roots():
    with pytest.raises(ValidationError, match="local filesystem paths"):
        CityProfile(
            city_name="Sampleville",
            timezone="America/Denver",
            file_drop_roots=["https://example.gov/dropbox"],
        )
