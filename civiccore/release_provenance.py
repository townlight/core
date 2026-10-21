"""Release provenance checks shared across Townlight modules.

GitHub release pages can show a Verified badge for the target commit even when
the release tag is lightweight or when an annotated tag object is unsigned.
Under the Townlight v1 provenance model, tags are release pointers and the
Sigstore-signed release attestation is the trust artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol


ATTESTATION_SCHEMA_VERSION = 1
GITHUB_ACTIONS_ISSUER = "https://token.actions.githubusercontent.com"
WEB_FLOW_KEY_ID = "B5690EEEBB952194"
ALLOWED_WEB_FLOW_COMMITTER = ("GitHub", "noreply@github.com")


class ProvenanceError(RuntimeError):
    """Raised when release provenance fails with an auditor-facing reason."""


class ProvenanceClient(Protocol):
    def tag_ref(self, repo: str, tag_name: str) -> dict[str, Any]: ...

    def tag_object(self, repo: str, tag_sha: str) -> dict[str, Any]: ...

    def commit(self, repo: str, commit_sha: str) -> dict[str, Any]: ...


class SigstoreVerifier(Protocol):
    def verify_blob(
        self,
        *,
        blob_path: Path,
        bundle_path: Path,
        expected_identity: str,
        expected_issuer: str,
    ) -> None: ...


class GitHubProvenanceClient:
    """Network-backed client for GitHub release provenance objects."""

    def _gh_api(self, path: str) -> dict[str, Any]:
        url = f"https://api.github.com/{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "civiccore-release-provenance",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProvenanceError(
                f"GitHub API request failed for {path}: HTTP {exc.code} {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProvenanceError(f"GitHub API request failed for {path}: {exc}") from exc

    def tag_ref(self, repo: str, tag_name: str) -> dict[str, Any]:
        return self._gh_api(f"repos/{repo}/git/ref/tags/{tag_name}")

    def tag_object(self, repo: str, tag_sha: str) -> dict[str, Any]:
        return self._gh_api(f"repos/{repo}/git/tags/{tag_sha}")

    def commit(self, repo: str, commit_sha: str) -> dict[str, Any]:
        return self._gh_api(f"repos/{repo}/commits/{commit_sha}")


class CosignSigstoreVerifier:
    """Verify Sigstore/cosign keyless bundles using the local cosign binary."""

    def verify_blob(
        self,
        *,
        blob_path: Path,
        bundle_path: Path,
        expected_identity: str,
        expected_issuer: str,
    ) -> None:
        if not bundle_path.exists():
            raise ProvenanceError(f"Missing Sigstore bundle: {bundle_path}")
        result = subprocess.run(
            [
                "cosign",
                "verify-blob",
                str(blob_path),
                "--bundle",
                str(bundle_path),
                "--certificate-identity",
                expected_identity,
                "--certificate-oidc-issuer",
                expected_issuer,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise ProvenanceError(
                "Sigstore verification failed for release attestation "
                f"with identity {expected_identity!r}: {detail}"
            )


class FixtureProvenanceClient:
    """Fixture-backed client for adversarial provenance test cases."""

    def __init__(self, fixture: dict[str, Any]) -> None:
        self.fixture = fixture
        self.responses = fixture["responses"]

    def tag_ref(self, repo: str, tag_name: str) -> dict[str, Any]:
        return self.responses["ref"]

    def tag_object(self, repo: str, tag_sha: str) -> dict[str, Any]:
        return self.responses.get("tag", {})

    def commit(self, repo: str, commit_sha: str) -> dict[str, Any]:
        return self.responses["commit"]


class FixtureSigstoreVerifier:
    """Fixture-backed Sigstore verifier for offline adversarial tests."""

    def __init__(self, fixture: dict[str, Any]) -> None:
        self.sigstore = fixture.get("sigstore", {})

    def verify_blob(
        self,
        *,
        blob_path: Path,
        bundle_path: Path,
        expected_identity: str,
        expected_issuer: str,
    ) -> None:
        if self.sigstore.get("availability") == "offline":
            raise ProvenanceError(
                "Sigstore transparency log is unavailable; use the documented offline "
                "bundle verification path or retry when online transparency proof is available."
            )
        if self.sigstore.get("trust_root_status") == "rotated":
            raise ProvenanceError(
                "Sigstore trust root changed; update the pinned trust-root bundle through "
                "the release-signing runbook before accepting this release."
            )
        actual_identity = self.sigstore.get("identity")
        if actual_identity != expected_identity:
            raise ProvenanceError(
                f"Sigstore identity {actual_identity!r} does not match expected "
                f"{expected_identity!r}."
            )
        actual_issuer = self.sigstore.get("issuer")
        if actual_issuer != expected_issuer:
            raise ProvenanceError(
                f"Sigstore issuer {actual_issuer!r} does not match expected "
                f"{expected_issuer!r}."
            )
        if not self.sigstore.get("verified", False):
            reason = self.sigstore.get("reason", "invalid")
            raise ProvenanceError(f"Sigstore bundle is not verified (reason: {reason}).")


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """Return Townlight's canonical JSON serialization for attestations."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def expected_workflow_identity(repo: str, tag_name: str, workflow: str = "release.yml") -> str:
    """Return the exact Sigstore workflow identity for a repo/tag release."""

    return f"https://github.com/{repo}/.github/workflows/{workflow}@refs/tags/{tag_name}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verification_reason(payload: dict[str, Any]) -> str:
    return str(payload.get("verification", {}).get("reason") or "missing")


def _require_verified(payload: dict[str, Any], label: str) -> None:
    verification = payload.get("verification") or {}
    if not verification.get("verified"):
        raise ProvenanceError(
            f"{label} is not GitHub-verified (reason: {_verification_reason(payload)})."
        )
    if verification.get("reason") != "valid":
        raise ProvenanceError(
            f"{label} verification reason is {verification.get('reason')!r}, expected 'valid'."
        )


def _require_web_flow_committer(commit: dict[str, Any], tag_name: str) -> None:
    committer = commit.get("commit", {}).get("committer") or {}
    actual = (committer.get("name"), committer.get("email"))
    if actual != ALLOWED_WEB_FLOW_COMMITTER:
        raise ProvenanceError(
            f"{tag_name} target commit committer is {actual[0]} <{actual[1]}>, "
            "expected GitHub <noreply@github.com> for the current web-flow commit model."
        )


def _require_expected_tree(commit: dict[str, Any], expected_tree: str | None, tag_name: str) -> None:
    if not expected_tree:
        return
    tree_sha = commit.get("commit", {}).get("tree", {}).get("sha")
    if tree_sha != expected_tree:
        raise ProvenanceError(
            f"{tag_name} target tree {tree_sha} does not match expected release tree "
            f"{expected_tree}; rebuild from the verified target commit before publishing."
        )


def _target_from_ref(
    client: ProvenanceClient,
    repo: str,
    tag_name: str,
    ref_object: dict[str, Any],
) -> tuple[str, str, str]:
    ref_type = ref_object["type"]
    ref_sha = ref_object["sha"]
    if ref_type == "commit":
        return ref_type, ref_sha, ref_sha
    if ref_type != "tag":
        raise ProvenanceError(f"{tag_name} tag ref points at {ref_type} {ref_sha}, not a commit.")
    tag_object = client.tag_object(repo, ref_sha)
    target = tag_object.get("object") or {}
    if target.get("type") != "commit":
        raise ProvenanceError(
            f"{tag_name} tag object points at {target.get('type')} {target.get('sha')}, "
            "not a commit."
        )
    return ref_type, ref_sha, target["sha"]


def _require_attestation_shape(attestation: dict[str, Any]) -> None:
    if attestation.get("schema_version") != ATTESTATION_SCHEMA_VERSION:
        raise ProvenanceError(
            "release-attestation.json schema_version must be 1; regenerate using the "
            "versioned Townlight Core attestation contract."
        )
    required_top = ("subject", "build", "artifacts")
    for key in required_top:
        if key not in attestation:
            raise ProvenanceError(f"release-attestation.json missing required field: {key}")
    if not isinstance(attestation["artifacts"], list) or not attestation["artifacts"]:
        raise ProvenanceError("release-attestation.json artifacts must be a non-empty list.")


def _require_attestation_subject(
    attestation: dict[str, Any],
    *,
    repo: str,
    tag_name: str,
    tag_ref_type: str,
    tag_ref_sha: str,
    target_commit: str,
    target_tree: str | None,
) -> None:
    subject = attestation["subject"]
    expected = {
        "repo": repo,
        "tag": tag_name,
        "tag_ref_type": tag_ref_type,
        "tag_ref_sha": tag_ref_sha,
        "target_commit": target_commit,
    }
    if target_tree:
        expected["target_tree"] = target_tree
    for key, expected_value in expected.items():
        actual = subject.get(key)
        if actual != expected_value:
            raise ProvenanceError(
                f"release-attestation.json subject.{key} {actual!r} does not match "
                f"expected {expected_value!r}."
            )


def _require_attestation_build(
    attestation: dict[str, Any],
    *,
    expected_identity: str,
    expected_issuer: str,
) -> None:
    build = attestation["build"]
    identity = build.get("workflow_identity")
    if identity != expected_identity:
        raise ProvenanceError(
            f"release-attestation.json build.workflow_identity {identity!r} does not match "
            f"expected {expected_identity!r}."
        )
    issuer = build.get("oidc_issuer")
    if issuer != expected_issuer:
        raise ProvenanceError(
            f"release-attestation.json build.oidc_issuer {issuer!r} does not match "
            f"expected {expected_issuer!r}."
        )
    workflow_path = build.get("workflow_path")
    if workflow_path != ".github/workflows/release.yml":
        raise ProvenanceError(
            f"release-attestation.json build.workflow_path {workflow_path!r} is not "
            "the approved release workflow path."
        )
    if not str(build.get("workflow_run_id") or "").strip():
        raise ProvenanceError("release-attestation.json build.workflow_run_id is required.")


def _require_artifact_hashes(attestation: dict[str, Any], artifacts_dir: Path | None) -> None:
    for artifact in attestation["artifacts"]:
        name = artifact.get("name")
        expected_hash = artifact.get("sha256")
        if not name or not expected_hash:
            raise ProvenanceError(
                "release-attestation.json artifact entries require name and sha256 fields."
            )
        if artifacts_dir is None:
            continue
        path = artifacts_dir / name
        if not path.exists():
            raise ProvenanceError(f"Attested artifact is missing from release assets: {name}")
        actual_hash = _sha256_file(path)
        if actual_hash != expected_hash:
            raise ProvenanceError(
                f"Attested artifact {name} sha256 {expected_hash} does not match "
                f"actual {actual_hash}."
            )


def verify_release_provenance(
    client: ProvenanceClient,
    repo: str,
    tag_name: str,
    *,
    attestation: dict[str, Any],
    sigstore_verifier: SigstoreVerifier,
    attestation_path: Path,
    bundle_path: Path,
    artifacts_dir: Path | None = None,
    expected_target: str | None = None,
    expected_tree: str | None = None,
) -> tuple[str, str]:
    """Verify a release pointer, target commit, signed attestation, and artifacts."""

    ref = client.tag_ref(repo, tag_name)
    tag_ref = ref["object"]
    tag_ref_type, tag_ref_sha, target_sha = _target_from_ref(client, repo, tag_name, tag_ref)
    if expected_target and target_sha != expected_target:
        raise ProvenanceError(
            f"{tag_name} tag target {target_sha} does not match expected target {expected_target}."
        )

    commit = client.commit(repo, target_sha)
    _require_verified(commit["commit"], f"{tag_name} target commit {target_sha}")
    _require_web_flow_committer(commit, tag_name)
    _require_expected_tree(commit, expected_tree, tag_name)
    target_tree = commit.get("commit", {}).get("tree", {}).get("sha")

    _require_attestation_shape(attestation)
    _require_attestation_subject(
        attestation,
        repo=repo,
        tag_name=tag_name,
        tag_ref_type=tag_ref_type,
        tag_ref_sha=tag_ref_sha,
        target_commit=target_sha,
        target_tree=target_tree,
    )
    expected_identity = expected_workflow_identity(repo, tag_name)
    _require_attestation_build(
        attestation,
        expected_identity=expected_identity,
        expected_issuer=GITHUB_ACTIONS_ISSUER,
    )
    _require_artifact_hashes(attestation, artifacts_dir)
    sigstore_verifier.verify_blob(
        blob_path=attestation_path,
        bundle_path=bundle_path,
        expected_identity=expected_identity,
        expected_issuer=GITHUB_ACTIONS_ISSUER,
    )
    return tag_ref_sha, target_sha


def _load_fixtures(fixtures_dir: Path) -> list[dict[str, Any]]:
    fixtures = []
    for path in sorted(fixtures_dir.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            fixture = json.load(handle)
        fixture["_path"] = str(path)
        fixtures.append(fixture)
    if not fixtures:
        raise ProvenanceError(f"No provenance fixtures found in {fixtures_dir}.")
    return fixtures


def _write_fixture_files(fixture: dict[str, Any], fixture_dir: Path) -> tuple[Path, Path, Path]:
    work_dir = fixture_dir / ".generated" / fixture["name"].replace(" ", "_")
    work_dir.mkdir(parents=True, exist_ok=True)
    attestation_path = work_dir / "release-attestation.json"
    bundle_path = work_dir / "release-attestation.json.bundle"
    artifacts_dir = work_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    attestation_path.write_bytes(canonical_json_bytes(fixture["attestation"]))
    bundle_path.write_text(json.dumps(fixture.get("bundle", {"fixture": True})), encoding="utf-8")
    for artifact in fixture.get("artifact_payloads", []):
        (artifacts_dir / artifact["name"]).write_bytes(artifact["content"].encode("utf-8"))
    return attestation_path, bundle_path, artifacts_dir


def run_fixtures(fixtures_dir: Path, repo: str) -> None:
    """Run adversarial release provenance fixtures."""

    failures = []
    for fixture in _load_fixtures(fixtures_dir):
        tag_name = fixture.get("tag_name", "vfixture")
        expected = fixture["expected"]
        expected_error = fixture.get("expected_error", "")
        try:
            attestation_path, bundle_path, artifacts_dir = _write_fixture_files(
                fixture,
                fixtures_dir,
            )
            verify_release_provenance(
                FixtureProvenanceClient(fixture),
                repo,
                tag_name,
                attestation=fixture["attestation"],
                sigstore_verifier=FixtureSigstoreVerifier(fixture),
                attestation_path=attestation_path,
                bundle_path=bundle_path,
                artifacts_dir=artifacts_dir,
                expected_target=fixture.get("expected_target"),
                expected_tree=fixture.get("expected_tree"),
            )
            actual = "pass"
            error = ""
        except ProvenanceError as exc:
            actual = "fail"
            error = str(exc)

        if actual != expected:
            failures.append(
                f"{fixture['_path']}: expected {expected}, got {actual}. Error: {error}"
            )
            continue
        if expected == "fail" and expected_error not in error:
            failures.append(
                f"{fixture['_path']}: failure did not include expected message "
                f"{expected_error!r}. Actual: {error}"
            )
            continue
        print(f"FIXTURE PASS: {fixture['name']} ({actual})")

    if failures:
        raise ProvenanceError("\n".join(failures))


def load_attestation(path: Path) -> dict[str, Any]:
    """Load a release attestation from disk."""

    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_release_attestation(
    *,
    repo: str,
    tag_name: str,
    tag_ref_type: str,
    tag_ref_sha: str,
    target_commit: str,
    target_tree: str,
    workflow_run_id: str,
    artifacts_dir: Path,
    evidence_bundles: list[dict[str, str]] | None = None,
    workflow_path: str = ".github/workflows/release.yml",
) -> dict[str, Any]:
    """Build a version 1 release attestation from local release artifacts."""

    artifacts = []
    for path in sorted(artifacts_dir.iterdir()):
        if not path.is_file() or path.name.endswith(".bundle"):
            continue
        artifacts.append({"name": path.name, "sha256": _sha256_file(path)})
    if not artifacts:
        raise ProvenanceError(f"No release artifacts found in {artifacts_dir}.")
    return {
        "schema_version": ATTESTATION_SCHEMA_VERSION,
        "subject": {
            "repo": repo,
            "tag": tag_name,
            "tag_ref_type": tag_ref_type,
            "tag_ref_sha": tag_ref_sha,
            "target_commit": target_commit,
            "target_tree": target_tree,
        },
        "build": {
            "workflow_identity": expected_workflow_identity(repo, tag_name, "release.yml"),
            "workflow_path": workflow_path,
            "workflow_run_id": workflow_run_id,
            "oidc_issuer": GITHUB_ACTIONS_ISSUER,
        },
        "artifacts": artifacts,
        "evidence_bundles": evidence_bundles or [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag_name", nargs="?", help="Release tag to verify, for example v0.22.0.")
    parser.add_argument(
        "--repo",
        default="CivicSuite/civiccore",
        help="GitHub repository in OWNER/REPO form.",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        help="Run the adversarial fixture suite before checking a live tag.",
    )
    parser.add_argument(
        "--attestation",
        type=Path,
        help="Path to release-attestation.json for the live release check.",
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        help="Path to the cosign bundle for release-attestation.json.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        help="Directory containing release assets named by the attestation.",
    )
    parser.add_argument(
        "--expected-target",
        help="Expected target commit SHA for pre-publication release gating.",
    )
    parser.add_argument(
        "--expected-tree",
        help="Expected target commit tree SHA for pre-publication artifact builds.",
    )
    args = parser.parse_args(argv)

    try:
        if args.fixtures_dir:
            run_fixtures(args.fixtures_dir, args.repo)
        if args.tag_name:
            if args.attestation is None or args.bundle is None:
                raise ProvenanceError(
                    "Live release verification requires --attestation and --bundle under "
                    "the Sigstore attestation provenance model."
                )
            tag_sha, target_sha = verify_release_provenance(
                GitHubProvenanceClient(),
                args.repo,
                args.tag_name,
                attestation=load_attestation(args.attestation),
                sigstore_verifier=CosignSigstoreVerifier(),
                attestation_path=args.attestation,
                bundle_path=args.bundle,
                artifacts_dir=args.artifacts_dir,
                expected_target=args.expected_target,
                expected_tree=args.expected_tree,
            )
            print(
                "PASS: release provenance verified "
                f"tag={args.tag_name} tag_ref={tag_sha} target_commit={target_sha} "
                f"attestation={args.attestation}"
            )
    except ProvenanceError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
