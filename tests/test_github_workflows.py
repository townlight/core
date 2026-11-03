from pathlib import Path

import yaml


def test_github_workflow_yaml_files_parse() -> None:
    workflow_dir = Path(".github/workflows")
    workflows = sorted(workflow_dir.glob("*.yml"))

    assert workflows
    for workflow in workflows:
        data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        assert isinstance(data, dict), workflow
        assert data.get("name"), workflow
        assert data.get("jobs"), workflow


def test_release_workflow_uploads_explicit_downloaded_asset_files() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    )
    workflow_dispatch = workflow[True]["workflow_dispatch"]
    release_tag = workflow_dispatch["inputs"]["release_tag"]
    tag_triggers = workflow[True]["push"]["tags"]
    draft_steps = workflow["jobs"]["create-draft-release"]["steps"]
    download_step = draft_steps[0]
    create_release_script = draft_steps[1]["run"]
    release_cleanroom = workflow["jobs"]["release-cleanroom-rehearsal"]
    publish_script = workflow["jobs"]["publish-release"]["steps"][0]["run"]

    assert release_tag["required"] is True
    assert release_tag["default"] == "v1.3.0.dev2"
    assert "v*" in tag_triggers
    assert "townlight_core-*-freeze" in tag_triggers
    assert workflow["jobs"]["cleanroom-rehearsal"]["if"] == "github.event_name == 'workflow_dispatch'"
    assert release_cleanroom["needs"] == ["create-draft-release"]
    assert workflow["jobs"]["publish-release"]["needs"] == ["release-cleanroom-rehearsal"]
    assert download_step["uses"] == "actions/download-artifact@v8"
    assert download_step["with"]["name"] == "townlight_core-dist"
    assert download_step["with"]["path"] == "release-assets/"
    assert "townlight_core-*-freeze) latest_flag=(--latest=false)" in create_release_script
    assert "Cleanroom rehearsal: PASSED in workflow run ${WORKFLOW_RUN_ID}" in create_release_script
    assert "Verified clean install of ${WHEEL_URL} from cold caches" in create_release_script
    assert "docs/evidence/co8-civiccore-procurement-evidence-pack/index.md" in create_release_script
    assert "docs/ops/co-9-civiccore-v1-closeout.md" in create_release_script
    assert "python scripts/verify-release-provenance.py ${TAG}" in create_release_script
    assert '"${latest_flag[@]}" \\' in create_release_script
    assert "--draft" in create_release_script
    assert "release-assets/dist/*" in create_release_script
    assert "release-assets/release-attestation.json \\" in create_release_script
    assert "release-assets/release-attestation.json.bundle \\" in create_release_script
    assert "release-assets/*" not in create_release_script
    assert "gh release download" in release_cleanroom["steps"][3]["run"]
    assert "python -m pip install --no-cache-dir --force-reinstall" in release_cleanroom["steps"][4]["run"]
    assert "TESTING=1 python" in release_cleanroom["steps"][4]["run"]
    assert "docker builder prune --all --force --filter \"label=townlight-cleanroom=1\"" in release_cleanroom["steps"][2]["run"]
    assert "system prune" not in release_cleanroom["steps"][2]["run"]
    assert "--draft=false" in publish_script
    assert "townlight_core-*-freeze) latest_flag=(--latest=false)" in publish_script


def test_ci_workflow_runs_full_release_verification_gate() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["tests"]["steps"]
    run_commands = [step.get("run", "") for step in steps]

    assert any("bash scripts/verify-release.sh" in command for command in run_commands)
    assert not any(command.startswith("pytest tests/test_smoke.py") for command in run_commands)


def test_release_gate_prefers_native_unix_python_before_windows_launcher() -> None:
    script = Path("scripts/verify-release.sh").read_text(encoding="utf-8")

    python3_index = script.index("command -v python3")
    python_exe_index = script.index("command -v python.exe")

    assert python3_index < python_exe_index


def test_co9_audit_report_has_post_publication_status() -> None:
    report = Path("docs/ops/co-9-audit-full-release-gate.md").read_text(encoding="utf-8")

    assert "Post-publication addendum" in report
    assert "| v1.0 release is published. | GitHub release page | True |" in report
    assert "Release tag is intentionally not created until after PR/main CI." not in report
    assert "Final `v1.0` Sigstore bundle cannot be verified until" not in report
