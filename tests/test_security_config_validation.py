from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from townlight_core.security import (
    ConfigValidationError,
    looks_like_placeholder,
    parse_csv_setting,
    validate_fernet_key_setting,
    validate_password_setting,
    validate_secret_setting,
)


@pytest.mark.parametrize(
    "value",
    ["<tenant-id>", "replace-with-real-value", "change-this-before-deploy"],
)
def test_placeholder_detection_matches_operator_templates(value: str) -> None:
    assert looks_like_placeholder(value) is True


def test_csv_setting_parser_accepts_env_strings_and_iterables() -> None:
    assert parse_csv_setting(" roles, groups, , department ") == ["roles", "groups", "department"]
    assert parse_csv_setting([" clerk ", "", "admin"]) == ["clerk", "admin"]
    assert parse_csv_setting(None) == []


@pytest.mark.parametrize("value", ["", "CHANGE-ME", "replace-with-secret", "too-short"])
def test_secret_validation_rejects_defaults_placeholders_and_short_values(value: str) -> None:
    with pytest.raises(ConfigValidationError):
        validate_secret_setting(value, setting_name="JWT_SECRET")


def test_secret_validation_accepts_long_random_looking_values() -> None:
    validate_secret_setting("a" * 64, setting_name="JWT_SECRET")


@pytest.mark.parametrize("value", ["", "CHANGE-ME", "CHANGE-ME-generate-with-fernet-generate-key", "<fernet-key>"])
def test_fernet_key_validation_rejects_placeholders(value: str) -> None:
    with pytest.raises(ConfigValidationError):
        validate_fernet_key_setting(value)


def test_fernet_key_validation_rejects_malformed_key() -> None:
    with pytest.raises(ConfigValidationError, match="valid Fernet key"):
        validate_fernet_key_setting("not-a-valid-fernet-key")


def test_fernet_key_validation_accepts_real_key() -> None:
    validate_fernet_key_setting(Fernet.generate_key().decode())


@pytest.mark.parametrize("value", ["CHANGE-ME-on-first-login", "password", "admin123", "short"])
def test_password_validation_rejects_common_or_short_values(value: str) -> None:
    with pytest.raises(ConfigValidationError):
        validate_password_setting(value, setting_name="FIRST_ADMIN_PASSWORD")


def test_password_validation_accepts_strong_password() -> None:
    validate_password_setting("S3cure!FreshAdminPwd-2026", setting_name="FIRST_ADMIN_PASSWORD")
