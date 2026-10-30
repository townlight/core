# SPDX-License-Identifier: AGPL-3.0-only
"""Contract tests for ``civiccore.scaffold`` (ADR-0007).

These tests assert the properties the beta plan actually needs, not a framework:
the generated project is a valid module by Core's own manifest contract, its code
imports and runs the shipped auth contract, the generator refuses unsafe names and
existing targets, every planned path stays inside the root, and nothing secret or
global is produced.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

import civiccore.scaffold
from civiccore.platform import ModuleManifest, build_module_registry, validate_windows_local_manifest
from civiccore.scaffold import (
    InvalidModuleSpecError,
    ModuleSpec,
    PathContainmentError,
    ScaffoldOptions,
    TargetExistsError,
    UnsafeTargetError,
    generate_module_project,
    plan_module_project,
)

CORE_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_SPEC = {
    "module_id": "civicnotes",
    "name": "CivicNotes (synthetic)",
    "description": "Synthetic module used to prove the generator contract.",
    "version": "0.1.0",
    "civiccore_min_version": "1.3.0.dev1",
    "staff_roles": ("notes_editor",),
    "route_path": "/notes",
}


def make_spec(**overrides) -> ModuleSpec:
    payload = {**SYNTHETIC_SPEC, **overrides}
    return ModuleSpec.model_validate(payload)


def test_spec_derives_every_identity_from_module_id() -> None:
    spec = make_spec(module_id="civic-note-book", route_path=None)
    assert spec.package_name == "civic_note_book"
    assert spec.token_roles_env_var == "CIVIC_NOTE_BOOK_TOKEN_ROLES"
    assert spec.permission == "civic-note-book-use"
    assert spec.route == "/civic-note-book"
    assert spec.baseline_revision == "civic_note_book_0001_baseline"


@pytest.mark.parametrize(
    "module_id",
    [
        "../escaped",
        "/absolute",
        "CivicNotes",
        "civic notes",
        "civicnotes;rm -rf",
        "notes.exe",
        "civiccore",
        "tests",
        "json",
        "import",
        "a",
        "-leading",
        "notes/sub",
    ],
)
def test_unsafe_or_reserved_module_ids_are_refused_not_sanitised(module_id: str) -> None:
    with pytest.raises(ValidationError):
        make_spec(module_id=module_id)

    with pytest.raises(InvalidModuleSpecError):
        civiccore.scaffold.spec.assert_admissible_module_id(module_id)


def test_plan_is_complete_and_pure(tmp_path: Path) -> None:
    spec = make_spec()
    plan = plan_module_project(spec)

    assert not any(tmp_path.iterdir())
    assert plan.project_root_name == "civicnotes"
    paths = set(plan.relative_paths)
    assert {
        "pyproject.toml",
        "README.md",
        ".gitignore",
        "src/civicnotes/__init__.py",
        "src/civicnotes/app.py",
        "src/civicnotes/manifest.py",
        "src/civicnotes/manifest.json",
        "migrations/env.py",
        "migrations/versions/civicnotes_0001_baseline.py",
        "tests/test_civicnotes_contract.py",
        "docs/module.md",
    } <= paths
    # Planning twice is deterministic; no timestamps, tokens or random ids.
    assert plan_module_project(spec).files == plan.files


def test_generated_manifest_is_valid_under_core_contracts() -> None:
    spec = make_spec()
    plan = plan_module_project(spec)
    payload = json.loads(
        next(item.content for item in plan.files if item.relative_path.endswith("manifest.json"))
    )

    manifest = validate_windows_local_manifest(ModuleManifest.model_validate(payload))
    assert manifest.module_id == "civicnotes"
    assert manifest.package_name == "civicnotes"
    assert manifest.enabled_by_default is False
    assert manifest.routes[0].permission == "civicnotes-use"
    assert manifest.migrations[0].id == "civicnotes_0001_baseline"

    # Off by default; an operator selects it explicitly and then it resolves enabled.
    default_registry = build_module_registry([payload], civiccore_version="1.3.0.dev1")
    assert default_registry.entries[0].status == "disabled"

    registry = build_module_registry(
        [payload],
        civiccore_version="1.3.0.dev1",
        selected_module_ids={"civicnotes"},
    )
    entry = registry.entries[0]
    assert entry.status == "enabled"
    assert "civicnotes" in registry.enabled_module_ids


def test_generated_sources_carry_agpl_spdx_and_no_secrets() -> None:
    plan = plan_module_project(make_spec())

    for item in plan.files:
        if item.relative_path.endswith(".py"):
            assert item.content.startswith("# SPDX-License-Identifier: AGPL-3.0-only"), (
                item.relative_path
            )
        assert "password" not in item.content.lower()
        assert "api_key" not in item.content.lower()
        assert not re.search(r"(?i)\b(secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]", item.content)

    pyproject = next(item.content for item in plan.files if item.relative_path == "pyproject.toml")
    assert 'license = "AGPL-3.0-only"' in pyproject
    assert "civiccore>=" in pyproject


def test_generated_health_probe_is_the_only_unauthenticated_route() -> None:
    """The generated module may expose liveness, but never staff data, anonymously."""

    plan = plan_module_project(make_spec())
    app_source = next(
        item.content for item in plan.files if item.relative_path.endswith("app.py")
    )
    decorators = re.findall(r"@app\.get\(\"([^\"]+)\"\)", app_source)

    assert decorators == ["/notes/health", "/notes"]
    health_block = app_source.split('@app.get("/notes/health")')[1].split("@app.get")[0]
    home_block = app_source.split('@app.get("/notes")')[1]
    assert "Depends" not in health_block
    assert "Depends(require_module_staff)" in home_block


def test_generated_project_imports_and_runs_the_auth_contract(tmp_path: Path) -> None:
    """The real proof: import the generated package and exercise its staff app."""

    spec = make_spec()
    result = generate_module_project(spec, tmp_path)
    src = result.project_root / "src"

    script = """
import json, os, sys
sys.path.insert(0, sys.argv[1])
from fastapi.testclient import TestClient
from civicnotes.app import TOKEN_ROLES_ENV_VAR, create_app
from civicnotes.manifest import load_manifest

manifest = load_manifest()
app = create_app()
os.environ.pop(TOKEN_ROLES_ENV_VAR, None)
unconfigured = TestClient(app).get("/notes").status_code
os.environ[TOKEN_ROLES_ENV_VAR] = '{"synthetic-runner-token": "notes_editor"}'
client = TestClient(app)
anonymous = client.get("/notes").status_code
unknown = client.get("/notes", headers={"Authorization": "Bearer nope"}).status_code
admitted = client.get("/notes", headers={"Authorization": "Bearer synthetic-runner-token"})
print(json.dumps({
    "module_id": manifest.module_id,
    "version": manifest.version,
    "unconfigured": unconfigured,
    "anonymous": anonymous,
    "unknown": unknown,
    "admitted_status": admitted.status_code,
    "admitted_body": admitted.json(),
    "health": client.get("/notes/health").json(),
}))
"""
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", script, str(src)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(CORE_ROOT)},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)

    assert payload["module_id"] == "civicnotes"
    assert payload["unconfigured"] == 503
    assert payload["anonymous"] == 401
    assert payload["unknown"] == 401
    assert payload["admitted_status"] == 200
    assert payload["admitted_body"]["roles"] == ["notes_editor"]
    assert payload["health"] == {"module_id": "civicnotes", "status": "ok"}


def test_generated_migration_owns_only_its_own_schema(tmp_path: Path) -> None:
    result = generate_module_project(make_spec(), tmp_path)
    baseline = (result.project_root / "migrations/versions/civicnotes_0001_baseline.py").read_text(
        encoding="utf-8"
    )
    env_py = (result.project_root / "migrations/env.py").read_text(encoding="utf-8")

    assert 'revision = "civicnotes_0001_baseline"' in baseline
    assert "down_revision = None" in baseline
    assert "CREATE SCHEMA IF NOT EXISTS civicnotes" in baseline
    assert "civiccore" not in baseline.replace("civiccore.scaffold", "")
    assert "DROP TABLE" not in baseline.split("def downgrade")[0]
    assert "upgrade_to_head" in env_py
    # Alembic creates its version table in civicnotes before the baseline revision runs,
    # so env.py's online path must create the schema first. Without this, a fresh database
    # fails with psycopg2.errors.InvalidSchemaName (found by the disposable PostgreSQL
    # acceptance fixture under work/beta-foundations/scaffold-01/pg-acceptance).
    online = env_py.split("def run_migrations_online")[1]
    assert 'CREATE SCHEMA IF NOT EXISTS civicnotes' in online
    assert online.index("CREATE SCHEMA IF NOT EXISTS civicnotes") < online.index(
        "context.configure("
    )


def test_generate_writes_project_and_never_overwrites(tmp_path: Path) -> None:
    spec = make_spec()
    first = generate_module_project(spec, tmp_path)

    assert first.dry_run is False
    assert set(first.created) == set(plan_module_project(spec).relative_paths)
    assert (first.project_root / "src/civicnotes/app.py").is_file()

    marker = first.project_root / "src/civicnotes/app.py"
    before = marker.read_text(encoding="utf-8")
    with pytest.raises(TargetExistsError):
        generate_module_project(spec, tmp_path)
    assert marker.read_text(encoding="utf-8") == before


def test_existing_target_directory_is_never_merged(tmp_path: Path) -> None:
    existing = tmp_path / "civicnotes"
    existing.mkdir()
    (existing / "keep.txt").write_text("pre-existing\n", encoding="utf-8")

    with pytest.raises(TargetExistsError):
        generate_module_project(make_spec(), tmp_path)
    assert (existing / "keep.txt").read_text(encoding="utf-8") == "pre-existing\n"
    assert sorted(path.name for path in existing.iterdir()) == ["keep.txt"]


def test_dry_run_plans_without_writing(tmp_path: Path) -> None:
    result = generate_module_project(make_spec(), tmp_path, options=ScaffoldOptions(dry_run=True))

    assert result.dry_run is True
    assert not (tmp_path / "civicnotes").exists()


def test_file_target_is_refused(tmp_path: Path) -> None:
    blocker = tmp_path / "civicnotes"
    blocker.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(UnsafeTargetError):
        generate_module_project(make_spec(), tmp_path)


def test_planned_paths_are_contained_and_parent_traversal_is_refused(monkeypatch) -> None:
    from civiccore.scaffold import project as project_module

    plan = plan_module_project(make_spec())
    poisoned = type(plan)(
        spec=plan.spec,
        project_root_name=plan.project_root_name,
        files=plan.files
        + (project_module.PlannedFile("../escape.txt", "x", ),),
    )
    with pytest.raises(PathContainmentError):
        project_module._assert_contained(poisoned)

    absolute = type(plan)(
        spec=plan.spec,
        project_root_name=plan.project_root_name,
        files=plan.files + (project_module.PlannedFile("/etc/passwd", "x"),),
    )
    with pytest.raises(PathContainmentError):
        project_module._assert_contained(absolute)


def test_symlinked_target_parent_cannot_redirect_writes(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError):  # pragma: no cover - Windows without privilege
        pytest.skip("symlink creation not permitted on this host")

    # A project created through the link still lands inside the resolved parent.
    result = generate_module_project(make_spec(), link)
    assert result.project_root.resolve().parent == real.resolve()


def test_cli_reports_refusal_and_creates_project(tmp_path: Path) -> None:
    good = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "civiccore.scaffold",
            "generate",
            "civicnotes",
            "--name",
            "CivicNotes (synthetic)",
            "--description",
            "Synthetic module used to prove the CLI contract.",
            "--staff-role",
            "notes_editor",
            "--route-path",
            "/notes",
            "--target",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(CORE_ROOT),
        check=False,
    )
    assert good.returncode == 0, good.stderr
    assert (tmp_path / "civicnotes/src/civicnotes/app.py").is_file()

    bad = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "civiccore.scaffold",
            "generate",
            "../escape",
            "--name",
            "Escape",
            "--description",
            "Synthetic refusal probe.",
            "--target",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(CORE_ROOT),
        check=False,
    )
    assert bad.returncode == 2
    assert "refused" in bad.stderr.lower()
    assert not (tmp_path / "escape").exists()
