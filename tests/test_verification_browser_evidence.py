from __future__ import annotations

import json
from pathlib import Path

import pytest

from townlight_core.verification import (
    BrowserReleaseEvidenceResult,
    normalized_text_sha256,
    validate_release_browser_evidence,
)


def test_normalized_text_sha256_treats_crlf_and_lf_as_same_content(tmp_path: Path) -> None:
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_text("alpha\nbeta\n", encoding="utf-8", newline="\n")
    crlf.write_text("alpha\nbeta\n", encoding="utf-8", newline="\r\n")

    assert normalized_text_sha256(lf) == normalized_text_sha256(crlf)


def test_validate_release_browser_evidence_accepts_matching_manifest(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    page = docs / "index.html"
    page.write_text("<main>Ready</main>\n", encoding="utf-8")
    desktop = docs / "desktop.png"
    mobile = docs / "mobile.png"
    desktop.write_bytes(b"x" * 25_000)
    mobile.write_bytes(b"y" * 25_000)
    manifest = docs / "release-evidence.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "0.1.2",
                "reviewed_at": "2026-04-29T09:32:51-06:00",
                "page": "docs/index.html",
                "page_sha256": normalized_text_sha256(page),
                "screenshots": {
                    "desktop": "docs/desktop.png",
                    "mobile": "docs/mobile.png",
                },
            }
        ),
        encoding="utf-8",
    )

    result = validate_release_browser_evidence(
        repo_root=tmp_path,
        manifest_path=manifest,
        expected_version="0.1.2",
    )

    assert isinstance(result, BrowserReleaseEvidenceResult)
    assert result.page == page
    assert result.screenshots["desktop"] == desktop
    assert result.screenshots["mobile"] == mobile


def test_validate_release_browser_evidence_rejects_hash_drift(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    page = docs / "index.html"
    page.write_text("<main>Ready</main>\n", encoding="utf-8")
    desktop = docs / "desktop.png"
    mobile = docs / "mobile.png"
    desktop.write_bytes(b"x" * 25_000)
    mobile.write_bytes(b"y" * 25_000)
    manifest = docs / "release-evidence.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "0.1.2",
                "reviewed_at": "2026-04-29T09:32:51-06:00",
                "page": "docs/index.html",
                "page_sha256": "deadbeef",
                "screenshots": {
                    "desktop": "docs/desktop.png",
                    "mobile": "docs/mobile.png",
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        validate_release_browser_evidence(
            repo_root=tmp_path,
            manifest_path=manifest,
            expected_version="0.1.2",
        )

    assert "hash mismatch" in str(exc_info.value)
