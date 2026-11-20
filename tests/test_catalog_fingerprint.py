import hashlib
import json

from townlight_core.catalog import fingerprint


def test_catalog_fingerprint_preserves_digest_across_database_collations():
    canonical_rows = [
        {"domain": "Utilities", "vendor_name": "CIS Infinity", "access_protocol": "odbc"},
        {"domain": "Utilities", "vendor_name": "Cartegraph", "access_protocol": "rest_api"},
    ]
    previous_digest = hashlib.sha256(
        json.dumps(canonical_rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    assert fingerprint(reversed(canonical_rows)) == previous_digest
    assert fingerprint(canonical_rows[:1]) != previous_digest
