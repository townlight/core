#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

TARGET_COMMIT="${1:-$(git rev-parse HEAD)}"
TARGET_COMMIT="$(git rev-parse "${TARGET_COMMIT}^{commit}")"
SHORT_SHA="${TARGET_COMMIT:0:12}"
EVIDENCE_ROOT="${2:-docs/evidence/co6-townlight_core-cleanroom-${SHORT_SHA}}"
RUN_COUNT="${CLEANROOM_RUN_COUNT:-2}"
IMAGE_TAG="townlight_core-cleanroom:${SHORT_SHA}"
REPO_URL="${TOWNLIGHT_CORE_REPO_URL:-https://github.com/townlight/core.git}"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required to run the TownlightCore cleanroom harness." >&2
    exit 1
fi

PYTHON_CMD=()
pick_python() {
    local -a candidate=("$@")
    if command -v "${candidate[0]}" >/dev/null 2>&1 && "${candidate[@]}" -c "import json, pathlib" >/dev/null 2>&1; then
        PYTHON_CMD=("${candidate[@]}")
        return 0
    fi
    return 1
}

if pick_python python; then
    :
elif pick_python python3; then
    :
elif pick_python python.exe; then
    :
elif pick_python py -3; then
    :
else
    echo "No usable Python interpreter found on PATH (checked python, python3, python.exe, py -3)." >&2
    exit 1
fi

if [ "${RUN_COUNT}" -lt 1 ]; then
    echo "CLEANROOM_RUN_COUNT must be at least 1." >&2
    exit 1
fi

host_path() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$1"
    else
        printf '%s' "$1"
    fi
}

run_dir_abs() {
    local path="$1"
    mkdir -p "${path}"
    (cd "${path}" && pwd)
}

echo "CO-6 cleanroom target commit: ${TARGET_COMMIT}"
echo "Evidence root: ${EVIDENCE_ROOT}"
echo "Run count: ${RUN_COUNT}"

DOCKER_BUILDKIT=1 docker build --no-cache --pull --platform linux/amd64 \
    --build-arg "TOWNLIGHT_CORE_REPO_URL=${REPO_URL}" \
    --build-arg "TOWNLIGHT_CORE_COMMIT=${TARGET_COMMIT}" \
    -f cleanroom/townlight_core.Dockerfile \
    -t "${IMAGE_TAG}" \
    .

rm -rf "${EVIDENCE_ROOT}"
mkdir -p "${EVIDENCE_ROOT}"

for idx in $(seq 1 "${RUN_COUNT}"); do
    label="run-${idx}"
    evidence_dir="${EVIDENCE_ROOT}/${label}"
    mkdir -p "${evidence_dir}"
    evidence_abs="$(run_dir_abs "${evidence_dir}")"
    evidence_mount="$(host_path "${evidence_abs}")"

    echo "Running online cleanroom phase: ${label}"
    MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --network bridge \
        -e "CLEANROOM_RUN_LABEL=${label}" \
        -e "TOWNLIGHT_CORE_COMMIT=${TARGET_COMMIT}" \
        -v "${evidence_mount}:/evidence" \
        "${IMAGE_TAG}" online

    echo "Running offline cleanroom phase: ${label}"
    MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --network none \
        -e "CLEANROOM_RUN_LABEL=${label}" \
        -e "TOWNLIGHT_CORE_COMMIT=${TARGET_COMMIT}" \
        -v "${evidence_mount}:/evidence" \
        "${IMAGE_TAG}" offline

    echo "Finalizing cleanroom evidence: ${label}"
    MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --network none \
        -e "CLEANROOM_RUN_LABEL=${label}" \
        -e "TOWNLIGHT_CORE_COMMIT=${TARGET_COMMIT}" \
        -v "${evidence_mount}:/evidence" \
        "${IMAGE_TAG}" finalize
done

"${PYTHON_CMD[@]}" - "${EVIDENCE_ROOT}" "${TARGET_COMMIT}" "${RUN_COUNT}" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
target_commit = sys.argv[2]
run_count = int(sys.argv[3])

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

manifests = []
for idx in range(1, run_count + 1):
    manifest_path = root / f"run-{idx}" / "cleanroom-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"missing manifest: {manifest_path}")
    manifests.append(
        {
            "run": f"run-{idx}",
            "path": str(manifest_path).replace("\\", "/"),
            "sha256": sha256(manifest_path),
            "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
        }
    )

manifest_hashes = [item["sha256"] for item in manifests]
identical = len(set(manifest_hashes)) == 1
comparison = {
    "schema_version": 1,
    "sprint_id": "CO-6",
    "target_commit": target_commit,
    "run_count": run_count,
    "identical_stable_manifests": identical,
    "manifest_hashes": [
        {"run": item["run"], "path": item["path"], "sha256": item["sha256"]}
        for item in manifests
    ],
    "timestamp_and_signature_note": (
        "run-metadata.json, manifest signatures, and compressed bundles are run-specific; "
        "cleanroom-manifest.json is the stable cross-machine comparison surface."
    ),
}
(root / "comparison.json").write_text(
    json.dumps(comparison, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

summary = [
    "# CO-6 TownlightCore Cleanroom Harness Evidence",
    "",
    f"Target commit: `{target_commit}`",
    f"Run count: {run_count}",
    f"Stable manifests identical: {str(identical).lower()}",
    "",
    "## Stable Manifest Hashes",
    "",
]
for item in comparison["manifest_hashes"]:
    summary.append(f"- `{item['run']}`: `{item['sha256']}`")
summary.extend(
    [
        "",
        "## Evidence",
        "",
        "- Each run directory contains `cleanroom-manifest.json`, logs, downloaded release assets, a signed manifest, and `cleanroom-evidence.tar.gz`.",
        "- `run-metadata.json`, signatures, and compressed bundle hashes are intentionally run-specific.",
        "- `comparison.json` is the machine-comparable summary.",
        "",
    ]
)
(root / "summary.md").write_text("\n".join(summary), encoding="utf-8")

if not identical:
    raise SystemExit("cleanroom stable manifests differ")
print(f"CO-6 cleanroom manifests match: {manifest_hashes[0]}")
PY
