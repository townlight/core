from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from townlight_core.release_provenance import (
    GitHubProvenanceClient,
    build_release_attestation,
    canonical_json_bytes,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_SCRIPT = REPO_ROOT / "scripts" / "verify-release-provenance.py"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "release_provenance"


def test_adversarial_release_provenance_fixtures_are_enforced() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PROVENANCE_SCRIPT),
            "--fixtures-dir",
            str(FIXTURES_DIR),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "FIXTURE PASS: known-good Sigstore attested release (pass)" in result.stdout
    assert "FIXTURE PASS: missing attestation schema is rejected (fail)" in result.stdout
    assert "FIXTURE PASS: wrong workflow identity is rejected (fail)" in result.stdout
    assert "FIXTURE PASS: mismatched artifact hash is rejected (fail)" in result.stdout
    assert "FIXTURE PASS: unexpected OIDC issuer is rejected (fail)" in result.stdout
    assert "FIXTURE PASS: transparency log outage fails closed (fail)" in result.stdout
    assert "FIXTURE PASS: attestation target mismatch is rejected (fail)" in result.stdout
    assert "FIXTURE PASS: workflow rename identity drift is rejected (fail)" in result.stdout
    assert "FIXTURE PASS: trust-root rotation fails closed (fail)" in result.stdout


def test_release_attestation_builder_uses_exact_workflow_identity(tmp_path: Path) -> None:
    artifact = tmp_path / "townlight_core-0.22.1-py3-none-any.whl"
    artifact.write_text("wheel bytes", encoding="utf-8")

    attestation = build_release_attestation(
        repo="Townlight/townlight_core",
        tag_name="v0.22.1",
        tag_ref_type="commit",
        tag_ref_sha="a" * 40,
        target_commit="a" * 40,
        target_tree="b" * 40,
        workflow_run_id="25346024240",
        artifacts_dir=tmp_path,
    )

    assert attestation["schema_version"] == 1
    assert (
        attestation["build"]["workflow_identity"]
        == "https://github.com/Townlight/townlight_core/.github/workflows/release.yml@refs/tags/v0.22.1"
    )
    assert attestation["build"]["oidc_issuer"] == "https://token.actions.githubusercontent.com"
    assert attestation["artifacts"] == [
        {
            "name": "townlight_core-0.22.1-py3-none-any.whl",
            "sha256": "67c0d8f7de19e30c2d5891030a0b37cbfcdd240852b53055c0b28290ad52290b",
        }
    ]
    assert canonical_json_bytes(attestation).decode("utf-8").startswith(
        '{"artifacts":[{"name":"townlight_core-0.22.1-py3-none-any.whl"'
    )


def test_github_provenance_client_uses_public_api_without_gh_cli(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"object":{"type":"commit","sha":"abc123"}}'

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("GH_TOKEN", "token-for-test")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = GitHubProvenanceClient().tag_ref("Townlight/townlight_core", "v0.22.1")

    assert result["object"]["sha"] == "abc123"
    assert captured["url"] == "https://api.github.com/repos/Townlight/townlight_core/git/ref/tags/v0.22.1"
    assert captured["headers"]["Authorization"] == "Bearer token-for-test"
    assert captured["headers"]["User-agent"] == "townlight_core-release-provenance"
    assert captured["timeout"] == 30
