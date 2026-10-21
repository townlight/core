from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "docs" / "ops" / "civiccore-tier1-retrofit-ledger.json"
LEDGER_CHECK = REPO_ROOT / "scripts" / "check-tier1-ledger.py"


def _ledger_check_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_tier1_ledger", LEDGER_CHECK)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_tier1_retrofit_ledger_static_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(LEDGER_CHECK), "--ledger", str(LEDGER)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "PASS: 25 Townlight Core release tags are ledgered" in result.stdout


def test_tier1_retrofit_ledger_marks_only_v0221_as_attested_baseline() -> None:
    ledger = _ledger()
    entries = ledger["entries"]
    baseline = [entry for entry in entries if entry["ledger_status"] == "attested_baseline"]
    pre_gate = [
        entry
        for entry in entries
        if entry["ledger_status"] == "pre_gate_no_attestation_do_not_promote"
    ]

    assert ledger["baseline_tag"] == "v0.22.1"
    assert [entry["tag"] for entry in baseline] == ["v0.22.1"]
    assert len(pre_gate) == 24
    assert all(entry["attestation_status"] == "none_pre_gate" for entry in pre_gate)
    assert all("release-attestation.json" not in entry["release_assets"] for entry in pre_gate)


def test_live_parity_allows_new_post_baseline_releases_with_attestation_assets() -> None:
    module = _ledger_check_module()
    entries = _ledger()["entries"]
    live_releases = {entry["tag"]: set(entry["release_assets"]) for entry in entries}
    live_releases["v1.0"] = {
        "civiccore-1.0.0-py3-none-any.whl",
        "civiccore-1.0.0.tar.gz",
        "SHA256SUMS.txt",
        "release-attestation.json",
        "release-attestation.json.bundle",
    }

    assert module.validate_live_release_parity(entries, live_releases) == ["v1.0"]


def test_live_parity_rejects_unledgered_releases_without_attestation_assets() -> None:
    module = _ledger_check_module()
    entries = _ledger()["entries"]
    live_releases = {entry["tag"]: set(entry["release_assets"]) for entry in entries}
    live_releases["v0.22.2"] = {"civiccore-0.22.2-py3-none-any.whl"}

    try:
        module.validate_live_release_parity(entries, live_releases)
    except module.LedgerError as exc:
        assert "v0.22.2" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("expected unledgered unattested release to fail")


def test_current_docs_do_not_describe_v0221_as_staged_or_unpublished() -> None:
    docs = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "README.txt",
        REPO_ROOT / "USER-MANUAL.md",
        REPO_ROOT / "USER-MANUAL.txt",
        REPO_ROOT / "docs" / "index.html",
    ]
    blocked_phrases = [
        "v0.22.1 is staged",
        "v0.22.1, once published",
        "staged baseline release candidate",
        "until the release workflow publishes its attestation",
    ]

    for path in docs:
        text = path.read_text(encoding="utf-8")
        for phrase in blocked_phrases:
            assert phrase not in text, f"{path} still contains {phrase!r}"
