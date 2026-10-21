#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-online}"
EVIDENCE_DIR="${CLEANROOM_EVIDENCE_DIR:-/evidence}"
RUN_LABEL="${CLEANROOM_RUN_LABEL:-cleanroom}"
RELEASE_TAG="${CLEANROOM_RELEASE_TAG:-v0.22.1}"
RELEASE_BASE_URL="https://github.com/CivicSuite/civiccore/releases/download/${RELEASE_TAG}"
OIDC_ISSUER="https://token.actions.githubusercontent.com"
WORKFLOW_IDENTITY="https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/${RELEASE_TAG}"

mkdir -p "${EVIDENCE_DIR}/logs" "${EVIDENCE_DIR}/release-assets"

log() {
    printf '[cleanroom:%s] %s\n' "${MODE}" "$*"
}

record_step() {
    local name="$1"
    local status="$2"
    printf '%s\t%s\n' "${name}" "${status}" >> "${EVIDENCE_DIR}/step-results.tsv"
}

run_step() {
    local name="$1"
    shift
    local log_file="${EVIDENCE_DIR}/logs/${name}.log"
    {
        printf 'step=%s\n' "${name}"
        printf 'cwd=%s\n' "$(pwd)"
        printf 'command='
        printf '%q ' "$@"
        printf '\n\n'
    } > "${log_file}"

    log "running ${name}"
    if "$@" >> "${log_file}" 2>&1; then
        record_step "${name}" "PASS"
    else
        record_step "${name}" "FAIL"
        tail -80 "${log_file}" >&2 || true
        exit 1
    fi
}

write_run_metadata() {
    python - <<'PY'
from __future__ import annotations

import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path

evidence = Path(os.environ["EVIDENCE_DIR"])
metadata_path = evidence / "run-metadata.json"
metadata = {}
if metadata_path.exists():
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
metadata.update(
    {
        "schema_version": 1,
        "sprint_id": "CO-6",
        "run_label": os.environ.get("RUN_LABEL", "cleanroom"),
        "mode_last_updated": os.environ.get("MODE", "unknown"),
        "updated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "target_commit": os.environ["CIVICCORE_COMMIT"],
        "repo_url": os.environ.get("CIVICCORE_REPO_URL", ""),
    }
)
metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

download_release_assets() {
    local assets=(
        "civiccore-0.22.1-py3-none-any.whl"
        "civiccore-0.22.1.tar.gz"
        "SHA256SUMS.txt"
        "release-attestation.json"
        "release-attestation.json.bundle"
    )
    for asset in "${assets[@]}"; do
        run_step "download-${asset}" \
            curl -fsSL --retry 3 --retry-delay 2 \
            -o "${EVIDENCE_DIR}/release-assets/${asset}" \
            "${RELEASE_BASE_URL}/${asset}"
    done
}

online() {
    export MODE RUN_LABEL EVIDENCE_DIR
    write_run_metadata
    run_step "verify-release" bash scripts/verify-release.sh
    run_step "verify-release-provenance-fixtures" \
        python scripts/verify-release-provenance.py --fixtures-dir tests/fixtures/release_provenance
    download_release_assets
    run_step "sha256sums-release-assets" \
        bash -lc "cd '${EVIDENCE_DIR}/release-assets' && sha256sum -c SHA256SUMS.txt"
    run_step "sigstore-release-attestation" \
        bash -lc "cd '${EVIDENCE_DIR}/release-assets' && cosign verify-blob release-attestation.json --bundle release-attestation.json.bundle --certificate-identity '${WORKFLOW_IDENTITY}' --certificate-oidc-issuer '${OIDC_ISSUER}'"
    run_step "live-release-provenance" \
        python scripts/verify-release-provenance.py "${RELEASE_TAG}" \
            --repo CivicSuite/civiccore \
            --attestation "${EVIDENCE_DIR}/release-assets/release-attestation.json" \
            --bundle "${EVIDENCE_DIR}/release-assets/release-attestation.json.bundle" \
            --artifacts-dir "${EVIDENCE_DIR}/release-assets"
}

offline() {
    export MODE RUN_LABEL EVIDENCE_DIR
    write_run_metadata
    run_step "offline-runtime-smoke" python - <<'PY'
import civiccore
import tomllib
from pathlib import Path

project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
assert civiccore.__version__ == project["project"]["version"]
assert callable(civiccore.validate_manifest)
assert callable(civiccore.import_meeting_payload)
assert callable(civiccore.plan_vendor_delta_request)
assert callable(civiccore.validate_cron_expression)
assert callable(civiccore.compute_onboarding_status)
assert callable(civiccore.verify_persisted_audit_chain)
print("offline runtime smoke OK")
PY
    run_step "offline-release-provenance-fixtures" \
        python scripts/verify-release-provenance.py --fixtures-dir tests/fixtures/release_provenance
}

finalize() {
    export MODE RUN_LABEL EVIDENCE_DIR
    write_run_metadata
    log "building stable manifest"
    python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

evidence = Path(os.environ["EVIDENCE_DIR"])
assets = evidence / "release-assets"
steps_path = evidence / "step-results.tsv"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

steps = []
for line in steps_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    name, status = line.split("\t", 1)
    steps.append({"name": name, "status": status})

if any(step["status"] != "PASS" for step in steps):
    raise SystemExit("cannot finalize evidence with failed steps")

release_assets = []
for path in sorted(assets.iterdir()):
    if path.is_file():
        release_assets.append({"name": path.name, "sha256": sha256(path)})

manifest = {
    "schema_version": 1,
    "sprint_id": "CO-6",
    "result": "PASS",
    "target": {
        "repo": "CivicSuite/civiccore",
        "repo_url": os.environ.get("CIVICCORE_REPO_URL", ""),
        "commit": os.environ["CIVICCORE_COMMIT"],
    },
    "container": {
        "base_image": os.environ["CLEANROOM_BASE_IMAGE"],
        "base_image_digest": os.environ["CLEANROOM_BASE_IMAGE_DIGEST"],
        "build_mode": "docker build --no-cache",
    },
    "cosign": {
        "version": os.environ["CLEANROOM_COSIGN_VERSION"],
        "linux_amd64_sha256": os.environ["CLEANROOM_COSIGN_SHA256"],
    },
    "release": {
        "tag": "v0.22.1",
        "workflow_identity": "https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/v0.22.1",
        "oidc_issuer": "https://token.actions.githubusercontent.com",
        "assets": release_assets,
    },
    "network": {
        "allowed_during_provisioning_and_verification": [
            "https://github.com/CivicSuite/civiccore.git",
            "https://github.com/CivicSuite/civiccore/releases/download/v0.22.1/*",
            "https://api.github.com/repos/CivicSuite/civiccore/*",
            "https://github.com/sigstore/cosign/releases/download/v3.0.6/cosign-linux-amd64",
            "https://pypi.org/*",
            "https://files.pythonhosted.org/*",
            "Sigstore transparency and certificate endpoints used by cosign verify-blob",
        ],
        "runtime_offline_proof": "offline-runtime-smoke and offline-release-provenance-fixtures ran in a docker run invocation with --network none.",
    },
    "commands": steps,
}

manifest_path = evidence / "cleanroom-manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(evidence / "cleanroom-manifest.sha256").write_text(
    f"{sha256(manifest_path)}  cleanroom-manifest.json\n",
    encoding="utf-8",
)
PY

    local private_key
    private_key="$(mktemp)"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "${private_key}" >/dev/null 2>&1
    openssl rsa -pubout -in "${private_key}" -out "${EVIDENCE_DIR}/evidence-signing-public.pem" >/dev/null 2>&1
    openssl dgst -sha256 -sign "${private_key}" \
        -out "${EVIDENCE_DIR}/cleanroom-manifest.json.sig" \
        "${EVIDENCE_DIR}/cleanroom-manifest.json"
    rm -f "${private_key}"
    openssl dgst -sha256 -verify "${EVIDENCE_DIR}/evidence-signing-public.pem" \
        -signature "${EVIDENCE_DIR}/cleanroom-manifest.json.sig" \
        "${EVIDENCE_DIR}/cleanroom-manifest.json" \
        > "${EVIDENCE_DIR}/signature-verify.log"

    (
        cd "${EVIDENCE_DIR}"
        find . -type f \
            ! -name 'files.sha256' \
            ! -name 'cleanroom-evidence.tar.gz' \
            ! -name 'cleanroom-evidence.tar.gz.sha256' \
            -print0 \
            | sort -z \
            | xargs -0 sha256sum > files.sha256
        tar --sort=name --mtime='UTC 2026-05-05' --owner=0 --group=0 --numeric-owner \
            -czf cleanroom-evidence.tar.gz \
            cleanroom-manifest.json \
            cleanroom-manifest.sha256 \
            cleanroom-manifest.json.sig \
            evidence-signing-public.pem \
            files.sha256 \
            logs \
            release-assets \
            run-metadata.json \
            signature-verify.log \
            step-results.tsv
        sha256sum cleanroom-evidence.tar.gz > cleanroom-evidence.tar.gz.sha256
    )
}

case "${MODE}" in
    online)
        online
        ;;
    offline)
        offline
        ;;
    finalize)
        finalize
        ;;
    *)
        echo "unknown cleanroom mode: ${MODE}" >&2
        exit 2
        ;;
esac
