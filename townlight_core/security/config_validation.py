"""Shared startup validation helpers for secret-bearing module settings."""

from __future__ import annotations

from collections.abc import Iterable

from cryptography.fernet import Fernet

DEFAULT_INSECURE_SECRET_VALUES = frozenset(
    {
        "",
        "CHANGE-ME",
        "CHANGE-ME-generate-with-openssl-rand-hex-32",
    }
)

DEFAULT_INSECURE_FERNET_KEY_VALUES = frozenset(
    {
        "",
        "CHANGE-ME",
        "CHANGE-ME-generate-with-fernet-generate-key",
    }
)

DEFAULT_INSECURE_PASSWORD_VALUES = frozenset(
    {
        "CHANGE-ME",
        "CHANGE-ME-on-first-login",
        "password",
        "Password",
        "PASSWORD",
        "admin",
        "Admin",
        "admin123",
        "Admin123",
        "changeme",
        "ChangeMe",
        "12345678",
        "123456789",
        "1234567890",
        "qwertyuiop",
        "letmein",
        "welcome",
        "Welcome1",
    }
)


class ConfigValidationError(ValueError):
    """Raised when a module setting is unsafe for startup."""


def looks_like_placeholder(value: str | None) -> bool:
    """Return True when a config value still looks like operator placeholder copy."""

    if value is None:
        return False
    lowered = value.lower()
    return "<" in value or ">" in value or "replace-" in lowered or "change-this" in lowered


def parse_csv_setting(value: str | Iterable[str] | None) -> list[str]:
    """Normalize CSV env values or native iterables into stripped non-empty strings."""

    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(part).strip() for part in value if str(part).strip()]


def validate_secret_setting(
    value: str | None,
    *,
    setting_name: str,
    min_length: int = 32,
    insecure_values: Iterable[str] = DEFAULT_INSECURE_SECRET_VALUES,
    generator_hint: str = "openssl rand -hex 32",
) -> None:
    """Raise when a generic secret is blank, a known placeholder, or too short."""

    secret = value or ""
    if secret in set(insecure_values) or looks_like_placeholder(secret):
        raise ConfigValidationError(
            f"{setting_name} is set to an insecure default. Generate a proper secret: {generator_hint}"
        )
    if len(secret) < min_length:
        raise ConfigValidationError(
            f"{setting_name} must be at least {min_length} characters (got {len(secret)}). "
            f"Generate one with: {generator_hint}"
        )


def validate_fernet_key_setting(
    value: str | None,
    *,
    setting_name: str = "ENCRYPTION_KEY",
    insecure_values: Iterable[str] = DEFAULT_INSECURE_FERNET_KEY_VALUES,
) -> None:
    """Raise unless a Fernet-compatible key is present and not a placeholder."""

    key = value or ""
    if key in set(insecure_values) or looks_like_placeholder(key):
        raise ConfigValidationError(
            f"{setting_name} is set to an insecure default. Generate a proper key:\n"
            '  python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"\n'
            "Back the key up SEPARATELY from the database; losing it means saved encrypted "
            "connection config becomes unreadable."
        )
    try:
        Fernet(key.encode("ascii"))
    except Exception as exc:
        raise ConfigValidationError(
            f"{setting_name} is not a valid Fernet key: {exc}. It must be 44 URL-safe "
            "base64 characters encoding a 32-byte key. Regenerate with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        ) from exc


def validate_password_setting(
    value: str | None,
    *,
    setting_name: str,
    min_length: int = 12,
    insecure_values: Iterable[str] = DEFAULT_INSECURE_PASSWORD_VALUES,
) -> None:
    """Raise when an operator-facing password is a placeholder, common value, or too short."""

    password = value or ""
    if password in set(insecure_values) or looks_like_placeholder(password):
        raise ConfigValidationError(
            f"{setting_name} is set to an insecure placeholder or common value. "
            f"Set it to a strong password (at least {min_length} characters, not in the common blocklist)."
        )
    if len(password) < min_length:
        raise ConfigValidationError(
            f"{setting_name} must be at least {min_length} characters (got {len(password)}). "
            "Set a strong value before starting the app."
        )


__all__ = [
    "ConfigValidationError",
    "DEFAULT_INSECURE_FERNET_KEY_VALUES",
    "DEFAULT_INSECURE_PASSWORD_VALUES",
    "DEFAULT_INSECURE_SECRET_VALUES",
    "looks_like_placeholder",
    "parse_csv_setting",
    "validate_fernet_key_setting",
    "validate_password_setting",
    "validate_secret_setting",
]
