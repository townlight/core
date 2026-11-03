"""Helpers for content-bound browser QA release evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


DEFAULT_MIN_SCREENSHOT_BYTES = 20_000


def normalized_text_sha256(path: Path) -> str:
    """Hash UTF-8 text content with normalized newlines for cross-platform parity."""

    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BrowserReleaseEvidenceResult:
    version: str
    reviewed_at: str
    page: Path
    screenshots: dict[str, Path]


def validate_release_browser_evidence(
    *,
    repo_root: Path,
    manifest_path: Path,
    expected_version: str,
    min_screenshot_bytes: int = DEFAULT_MIN_SCREENSHOT_BYTES,
) -> BrowserReleaseEvidenceResult:
    """Validate a release browser-evidence manifest and raise actionable errors on drift."""

    if not manifest_path.exists():
        raise ValueError(f"Missing browser evidence manifest: {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = _require_non_empty_str(data, "version")
    if version != expected_version:
        raise ValueError(
            f"Browser evidence version mismatch: expected {expected_version}, found {version!r}."
        )

    reviewed_at = _require_non_empty_str(data, "reviewed_at")
    page_rel = _require_non_empty_str(data, "page")
    page = repo_root / page_rel
    if not page.exists():
        raise ValueError(f"Browser evidence page is missing: {page_rel}")

    expected_hash = _require_non_empty_str(data, "page_sha256")
    actual_hash = normalized_text_sha256(page)
    if actual_hash != expected_hash:
        raise ValueError(
            "Browser evidence page hash mismatch; refresh browser QA screenshots and manifest."
        )

    screenshots_raw = data.get("screenshots")
    if not isinstance(screenshots_raw, dict):
        raise ValueError("Browser evidence manifest is missing a screenshots map.")

    screenshots: dict[str, Path] = {}
    for viewport in ("desktop", "mobile"):
        rel_path = screenshots_raw.get(viewport)
        if not isinstance(rel_path, str) or not rel_path.strip():
            raise ValueError(f"Browser evidence manifest is missing the {viewport} screenshot path.")
        screenshot = repo_root / rel_path
        if not screenshot.exists():
            raise ValueError(f"Missing browser evidence screenshot: {rel_path}")
        if screenshot.stat().st_size <= min_screenshot_bytes:
            raise ValueError(f"Browser evidence screenshot is too small to trust: {rel_path}")
        screenshots[viewport] = screenshot

    return BrowserReleaseEvidenceResult(
        version=version,
        reviewed_at=reviewed_at,
        page=page,
        screenshots=screenshots,
    )


def _require_non_empty_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Browser evidence manifest is missing {key}.")
    return value
