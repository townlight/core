from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_cleanroom_dockerfile_pins_base_image_and_cosign() -> None:
    dockerfile = read("cleanroom/civiccore.Dockerfile")

    assert "python:3.13-slim-bookworm@sha256:bb73517d48bd32016e15eade0c009b2724ec3a025a9975b5cd9b251d0dcadb33" in dockerfile
    assert "ARG COSIGN_VERSION=v3.0.6" in dockerfile
    assert "ARG COSIGN_SHA256=c956e5dfcac53d52bcf058360d579472f0c1d2d9b69f55209e256fe7783f4c74" in dockerfile
    assert "git fetch --depth 1 origin" in dockerfile
    assert 'test "$(git rev-parse HEAD)" = "${CIVICCORE_COMMIT}"' in dockerfile


def test_cleanroom_runner_executes_required_verification_paths() -> None:
    runner = read("scripts/cleanroom/civiccore-cleanroom-runner.sh")

    assert "bash scripts/verify-release.sh" in runner
    assert "python scripts/verify-release-provenance.py --fixtures-dir tests/fixtures/release_provenance" in runner
    assert "cosign verify-blob release-attestation.json" in runner
    assert "sha256sum -c SHA256SUMS.txt" in runner
    assert "python scripts/verify-release-provenance.py \"${RELEASE_TAG}\"" in runner
    assert "offline-runtime-smoke" in runner
    assert "cleanroom-manifest.json.sig" in runner


def test_cleanroom_orchestrator_uses_no_cache_two_runs_and_offline_network() -> None:
    orchestrator = read("scripts/run-civiccore-cleanroom.sh")

    assert "docker build --no-cache --pull --platform linux/amd64" in orchestrator
    assert "RUN_COUNT=\"${CLEANROOM_RUN_COUNT:-2}\"" in orchestrator
    assert "pick_python" in orchestrator
    assert '"${candidate[@]}" -c "import json, pathlib"' in orchestrator
    assert "--network none" in orchestrator
    assert "cleanroom stable manifests differ" in orchestrator


def test_cleanroom_ci_uploads_evidence_artifact() -> None:
    workflow = read(".github/workflows/cleanroom.yml")

    assert "TARGET_COMMIT" in workflow
    assert "github.event.pull_request.head.sha" in workflow
    assert "fetch-depth: 0" in workflow
    assert "bash scripts/run-civiccore-cleanroom.sh" in workflow
    assert "actions/upload-artifact" in workflow
    assert "CLEANROOM_RUN_COUNT: \"2\"" in workflow


@pytest.mark.parametrize("runtime_version", ["9.8.7", "0.22.1", "1.2.1"])
def test_offline_smoke_requires_candidate_version(
    tmp_path: Path, runtime_version: str
) -> None:
    runner = read("scripts/cleanroom/civiccore-cleanroom-runner.sh")
    marker = 'run_step "offline-runtime-smoke" python - <<\'PY\'\n'
    smoke = runner.split(marker, 1)[1].split("\nPY", 1)[0]
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "9.8.7"\n', encoding="utf-8"
    )
    exports = (
        "validate_manifest",
        "import_meeting_payload",
        "plan_vendor_delta_request",
        "validate_cron_expression",
        "compute_onboarding_status",
        "verify_persisted_audit_chain",
    )
    (tmp_path / "civiccore.py").write_text(
        f"__version__ = {runtime_version!r}\n"
        + "".join(f"def {name}(): pass\n" for name in exports),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-c", smoke], cwd=tmp_path, capture_output=True, text=True
    )

    if runtime_version == "9.8.7":
        assert result.returncode == 0, result.stderr
        assert "offline runtime smoke OK" in result.stdout
    else:
        assert result.returncode != 0
        assert "AssertionError" in result.stderr
