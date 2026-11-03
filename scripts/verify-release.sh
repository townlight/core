#!/usr/bin/env bash
# townlight_core/scripts/verify-release.sh - townlight_core release gate.
#
# Read-only verification of townlight_core's pre-push readiness. Checks:
#   1. Test suite (pytest tests/)
#   2. Lint (ruff check .)
#   3. Version lockstep between pyproject.toml and townlight_core/__init__.py
#   4. Required Rule 9 doc artifacts present on disk
#   5. Build artifacts (sdist + wheel via python -m build)
#   6. Fresh virtualenv install from the built wheel, exact version check,
#      and import smoke for the migration runner
#   7. Release-provenance adversarial fixture suite
#
# Exit 0 when every check passes; exit 1 on any failure.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_CMD=()
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=(python3)
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=(python)
elif command -v py >/dev/null 2>&1; then
    PYTHON_CMD=(py -3)
elif command -v python.exe >/dev/null 2>&1; then
    PYTHON_CMD=(python.exe)
else
    echo "No Python interpreter found on PATH (checked python3, python, py, python.exe)." >&2
    exit 1
fi

FAILED=0
pass() { printf '  \033[0;32m[PASS]\033[0m %s\n' "$*"; }
fail() { printf '  \033[0;31m[FAIL]\033[0m %s\n' "$*" >&2; FAILED=1; }
info() { printf '\n\033[1;34m%s\033[0m\n' "$*"; }

RELEASE_VENV=""
cleanup() {
    if [ -n "$RELEASE_VENV" ] && [ -d "$RELEASE_VENV" ]; then
        rm -rf "$RELEASE_VENV"
    fi
}
trap cleanup EXIT

dump_failure_diagnostics() {
    echo ""
    echo "============================================"
    echo "  Release verification diagnostics"
    echo "============================================"
    echo ""
    echo "## python"
    "${PYTHON_CMD[@]}" -c 'import sys; print(sys.executable); print(sys.version)' || true
    echo ""
    echo "## installed release-tool packages"
    "${PYTHON_CMD[@]}" -m pip show pytest ruff build pydantic 2>/dev/null || true
    echo ""
    if [ -f docker-compose.yml ] || [ -f docker-compose.yaml ] || [ -f compose.yml ] || [ -f compose.yaml ]; then
        echo "## docker compose ps"
        docker compose ps || true
        echo ""
        echo "## docker compose logs --no-color --tail 100"
        docker compose logs --no-color --tail 100 || true
        echo ""
    else
        echo "## docker compose"
        echo "No compose file present; TownlightCore release verification is package-only."
        echo ""
    fi
    echo "============================================"
    echo ""
}

info "0. release verification environment"
RELEASE_VENV="$(mktemp -d "${TMPDIR:-/tmp}/townlight_core-release-env-XXXXXX")"
if "${PYTHON_CMD[@]}" -m venv "$RELEASE_VENV"; then
    VENV_PYTHON="$RELEASE_VENV/bin/python"
    if [ ! -x "$VENV_PYTHON" ] && [ -x "$RELEASE_VENV/Scripts/python.exe" ]; then
        VENV_PYTHON="$RELEASE_VENV/Scripts/python.exe"
    fi
    if [ -x "$VENV_PYTHON" ]; then
        PYTHON_CMD=("$VENV_PYTHON")
        if "${PYTHON_CMD[@]}" -m pip install --upgrade pip >/dev/null \
            && "${PYTHON_CMD[@]}" -m pip install -e ".[dev]" >/dev/null; then
            pass "temporary release environment bootstrapped"
        else
            fail "temporary release environment dependency install failed"
        fi
    else
        fail "temporary release environment python executable missing"
    fi
else
    fail "temporary release environment creation failed"
fi

# --- 1. pytest ---------------------------------------------------------------
info "1. pytest"
if "${PYTHON_CMD[@]}" -m pytest tests/ -v --tb=short; then
    pass "test suite green"
else
    fail "pytest failed"
fi

# --- 2. ruff -----------------------------------------------------------------
info "2. ruff check"
if "${PYTHON_CMD[@]}" -m ruff check .; then
    pass "lint clean"
else
    fail "ruff reported issues"
fi

# --- 3. version lockstep (pyproject.toml <-> townlight_core/__init__.py) ---------
info "3. version lockstep"
PY_VER=$(grep -oE '^version[[:space:]]*=[[:space:]]*"[^"]+"' pyproject.toml 2>/dev/null \
    | head -1 \
    | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)"/\1/' || true)
INIT_VER=$(grep -oE '__version__[[:space:]]*=[[:space:]]*"[^"]+"' townlight_core/__init__.py 2>/dev/null \
    | head -1 \
    | sed -E 's/.*"([^"]+)"/\1/' || true)

printf '      pyproject.toml          %s\n' "${PY_VER:-<missing>}"
printf '      townlight_core/__init__.py   %s\n' "${INIT_VER:-<missing>}"

if [ -n "$PY_VER" ] && [ -n "$INIT_VER" ] && [ "$PY_VER" = "$INIT_VER" ]; then
    pass "two surfaces agree on $PY_VER"
else
    fail "version mismatch - surfaces do not agree"
fi

# --- 3b. release provenance fixtures ----------------------------------------
info "3b. release provenance fixtures"
if "${PYTHON_CMD[@]}" scripts/verify-release-provenance.py --fixtures-dir tests/fixtures/release_provenance; then
    pass "release provenance fixture suite enforced"
else
    fail "release provenance fixture suite failed"
fi

# --- 4. required docs --------------------------------------------------------
info "4. required docs present"
for f in README.md CHANGELOG.md CONTRIBUTING.md LICENSE .gitignore docs/index.html; do
    if [ -f "$f" ]; then
        pass "$f"
    else
        fail "missing: $f"
    fi
done

# --- 5. build artifacts ------------------------------------------------------
info "5. build artifacts"
rm -rf dist/ build/
if "${PYTHON_CMD[@]}" -m build; then
    pass "python -m build succeeded"
else
    fail "python -m build failed"
fi

# --- 6. wheel install in a clean virtualenv ---------------------------------
info "6. clean virtualenv wheel install"
if "${PYTHON_CMD[@]}" - <<'PY'
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def main() -> int:
    wheels = sorted(glob.glob("dist/townlight_core-*.whl"))
    if not wheels:
        print("missing built wheel in dist/", file=sys.stderr)
        return 1

    wheel_path = Path(wheels[0]).resolve()
    temp_dir = Path(tempfile.mkdtemp(prefix="townlight_core-release-"))

    try:
        builder = venv.EnvBuilder(with_pip=True)
        builder.create(temp_dir)

        candidates = [
            temp_dir / "Scripts" / "python.exe",
            temp_dir / "Scripts" / "python",
            temp_dir / "bin" / "python",
        ]
        venv_python = next((path for path in candidates if path.exists()), None)
        if venv_python is None:
            print("could not locate virtualenv python executable", file=sys.stderr)
            return 1

        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", str(wheel_path)],
            check=True,
        )
        subprocess.run(
            [
                str(venv_python),
                "-c",
                (
                    "from pathlib import Path; "
                    "import re; "
                    "from importlib.metadata import version; "
                    "import townlight_core; "
                    "from townlight_core.migrations.runner import upgrade_to_head; "
                    "pyproject = Path('pyproject.toml').read_text(encoding='utf-8'); "
                    "match = re.search(r'^version\\s*=\\s*\"([^\"]+)\"', pyproject, re.MULTILINE); "
                    "assert match, 'pyproject.toml version missing'; "
                    "expected_version = match.group(1); "
                    "assert version('townlight_core') == expected_version; "
                    "assert townlight_core.__version__ == expected_version; "
                    "assert callable(upgrade_to_head); "
                    "assert callable(townlight_core.validate_manifest); "
                    "assert callable(townlight_core.ingest_file); "
                    "assert callable(townlight_core.ingest_bytes); "
                    "assert callable(townlight_core.register_handler); "
                    "assert townlight_core.Document; "
                    "assert townlight_core.DocumentChunk; "
                    "assert townlight_core.DataSource; "
                    "assert callable(townlight_core.import_meeting_payload); "
                    "assert callable(townlight_core.plan_vendor_delta_request); "
                    "assert callable(townlight_core.build_deadline_plan); "
                    "assert callable(townlight_core.evaluate_notice_compliance); "
                    "assert callable(townlight_core.validate_cron_expression); "
                    "assert callable(townlight_core.compute_next_sync_at); "
                    "assert callable(townlight_core.compute_onboarding_status); "
                    "assert callable(townlight_core.next_profile_prompt); "
                    "assert townlight_core.AuditHashChain; "
                    "assert townlight_core.PersistedAuditLogEntry; "
                    "assert callable(townlight_core.compute_persisted_audit_hash); "
                    "assert callable(townlight_core.verify_persisted_audit_chain); "
                    "assert townlight_core.SyncCircuitState; "
                    "assert townlight_core.SyncRunResult; "
                    "assert townlight_core.SyncSourceStatus; "
                    "assert callable(townlight_core.apply_sync_run_result); "
                    "assert callable(townlight_core.build_sync_source_status); "
                    "assert callable(townlight_core.with_http_retry); "
                    "assert townlight_core.CityProfile; "
                    "assert callable(townlight_core.reciprocal_rank_fusion); "
                    "print('fresh-venv import smoke OK')"
                ),
            ],
            check=True,
        )
        print(f"fresh virtualenv install verified via {venv_python}")
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


raise SystemExit(main())
PY
then
    pass "fresh virtualenv import + exact version verification succeeded"
else
    fail "fresh virtualenv import/version verification failed"
fi

# --- summary -----------------------------------------------------------------
echo ""
if [ "$FAILED" -eq 0 ]; then
    printf '\033[0;32mVERIFY-RELEASE: PASSED\033[0m\n'
    exit 0
else
    printf '\033[0;31mVERIFY-RELEASE: FAILED\033[0m\n'
    dump_failure_diagnostics
    exit 1
fi
