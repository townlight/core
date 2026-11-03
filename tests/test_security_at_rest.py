from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from townlight_core.security import AtRestDecryptionError, decrypt_json, encrypt_json, is_encrypted


def test_encrypt_json_round_trips_dict_payload() -> None:
    key = Fernet.generate_key().decode("ascii")

    encrypted = encrypt_json({"api_key": "secret", "retries": 3}, encryption_key=key)
    decrypted = decrypt_json(encrypted, encryption_key=key)

    assert is_encrypted(encrypted) is True
    assert decrypted == {"api_key": "secret", "retries": 3}


def test_encrypt_json_rejects_non_dict_payloads() -> None:
    key = Fernet.generate_key().decode("ascii")

    with pytest.raises(TypeError, match="expects a dict"):
        encrypt_json(["not", "a", "dict"], encryption_key=key)  # type: ignore[arg-type]


def test_decrypt_json_rejects_plaintext_payloads() -> None:
    key = Fernet.generate_key().decode("ascii")

    with pytest.raises(AtRestDecryptionError, match="pre-encryption plaintext"):
        decrypt_json({"api_key": "secret"}, encryption_key=key)


def test_decrypt_json_rejects_wrong_key() -> None:
    key = Fernet.generate_key().decode("ascii")
    wrong_key = Fernet.generate_key().decode("ascii")
    encrypted = encrypt_json({"api_key": "secret"}, encryption_key=key)

    with pytest.raises(AtRestDecryptionError, match="Fernet rejected the ciphertext"):
        decrypt_json(encrypted, encryption_key=wrong_key)
