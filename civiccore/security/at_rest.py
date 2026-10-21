"""Shared encrypted-JSON envelope helpers for secret-bearing config blobs."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

ENVELOPE_VERSION = 1


class AtRestDecryptionError(Exception):
    """Raised when an encrypted JSON payload cannot be decrypted safely."""


def build_fernet(encryption_key: str) -> Fernet:
    """Build a Fernet instance from an ASCII key string."""

    return Fernet(encryption_key.encode("ascii"))


def encrypt_json(obj: dict[str, Any], *, encryption_key: str) -> dict[str, Any]:
    """Encrypt a dict into the versioned envelope shape used by Townlight."""

    if not isinstance(obj, dict):
        raise TypeError(
            f"encrypt_json expects a dict, got {type(obj).__name__}. "
            "Secret-bearing connection config must be a JSON object."
        )
    plaintext = json.dumps(obj, sort_keys=True).encode("utf-8")
    token = build_fernet(encryption_key).encrypt(plaintext).decode("ascii")
    return {"v": ENVELOPE_VERSION, "ct": token}


def decrypt_json(payload: Any, *, encryption_key: str) -> dict[str, Any]:
    """Decrypt a versioned envelope back to the original dict."""

    if not isinstance(payload, dict):
        raise AtRestDecryptionError(
            f"Envelope must be a dict, got {type(payload).__name__}. "
            "The stored value is likely plaintext and needs a migration pass."
        )
    if "v" not in payload:
        raise AtRestDecryptionError(
            "Envelope is missing the 'v' version field; the stored value is likely "
            "pre-encryption plaintext and needs a migration pass."
        )
    version = payload["v"]
    if version != ENVELOPE_VERSION:
        raise AtRestDecryptionError(
            f"Unknown envelope version v={version!r}. "
            f"This codebase only knows how to decrypt v={ENVELOPE_VERSION}."
        )
    token = payload.get("ct")
    if not isinstance(token, str):
        raise AtRestDecryptionError("Envelope is missing a string 'ct' ciphertext field.")
    try:
        plaintext = build_fernet(encryption_key).decrypt(token.encode("ascii"))
    except InvalidToken as exc:
        raise AtRestDecryptionError(
            "Fernet rejected the ciphertext: either the encryption key has changed "
            "without a re-encryption pass, or the stored value has been tampered with."
        ) from exc
    return json.loads(plaintext.decode("utf-8"))


def is_encrypted(value: Any) -> bool:
    """Return True when a value already matches the expected envelope shape."""

    return (
        isinstance(value, dict)
        and value.get("v") == ENVELOPE_VERSION
        and isinstance(value.get("ct"), str)
    )


__all__ = [
    "AtRestDecryptionError",
    "ENVELOPE_VERSION",
    "build_fernet",
    "decrypt_json",
    "encrypt_json",
    "is_encrypted",
]
