# Release Signing and Provenance

Townlight Core is the canonical home for Townlight release-provenance gate logic.
Downstream modules should call `python -m civiccore.release_provenance` or a
thin local wrapper around `civiccore.release_provenance.main()`.

Release provenance is a pre-flight gate, not post-publication forensics. A
failing gate produces no release assets. There is no dev-process exemption, no
localhost identity exception, and no "fix it in the next release" path.

## Current Trust Model

GitHub release pages can show a "Verified" badge for the target commit even
when the release tag itself is lightweight or when an annotated tag object is
unsigned. Townlight does not treat the tag as the trust root. The tag is a
release pointer. The trust artifact is a Sigstore-signed
`release-attestation.json` produced by the exact release workflow for the exact
repo and tag.

The acceptable release shape is:

1. Merge the release PR through GitHub so the target commit is web-flow signed.
2. Build release artifacts and `SHA256SUMS.txt`.
3. Generate `release-attestation.json` using the version 1 schema in
   `docs/ops/release-attestation.schema.json`.
4. Serialize the attestation canonically with sorted JSON object keys, no extra
   whitespace, and UTF-8 bytes. In Python, use
   `civiccore.release_provenance.canonical_json_bytes()`.
5. Sign the attestation with keyless Sigstore/cosign from GitHub Actions OIDC.
6. Run the adversarial fixture suite before checking the real release:

   ```bash
   python scripts/verify-release-provenance.py --fixtures-dir tests/fixtures/release_provenance
   ```

7. Run the live provenance gate before publishing release assets:

   ```bash
   python scripts/verify-release-provenance.py vX.Y.Z \
     --repo CivicSuite/civiccore \
     --attestation release-attestation.json \
     --bundle release-attestation.json.bundle \
     --artifacts-dir dist \
     --expected-target <verified-target-commit-sha> \
     --expected-tree <verified-release-tree-sha>
   ```

8. Publish the GitHub Release and assets only after the pre-flight gate passes.

The exact Sigstore certificate identity must be pinned per repo and per tag:

```text
https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/vX.Y.Z
```

Do not replace this with an org-wide or repo-wide wildcard. A wildcard requires
a written auditor-reviewed justification and a fixture proving the widened
scope cannot verify another repo's release.

## Version 1 Attestation Contract

`release-attestation.json` has schema version `1` and must include:

- `subject.repo`
- `subject.tag`
- `subject.tag_ref_type`
- `subject.tag_ref_sha`
- `subject.target_commit`
- `subject.target_tree`
- `build.workflow_identity`
- `build.workflow_path`
- `build.workflow_run_id`
- `build.oidc_issuer`
- `artifacts[].name`
- `artifacts[].sha256`
- `evidence_bundles[].name`
- `evidence_bundles[].sha256`

The schema is locked in `docs/ops/release-attestation.schema.json`. Schema
changes require a new schema version and consumer rollout plan; do not add
ad-hoc per-release fields.

## Consumer Verification

For online verification, download the release assets and run:

```bash
cosign verify-blob release-attestation.json \
  --bundle release-attestation.json.bundle \
  --certificate-identity "https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/vX.Y.Z" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

sha256sum -c SHA256SUMS.txt
python scripts/verify-release-provenance.py vX.Y.Z \
  --repo CivicSuite/civiccore \
  --attestation release-attestation.json \
  --bundle release-attestation.json.bundle \
  --artifacts-dir .
```

For disconnected procurement review, preserve the cosign bundle, release
attestation, release assets, `SHA256SUMS.txt`, the pinned cosign version, and
the Sigstore trust-root bundle used by the release workflow. Offline review
uses the bundle and pinned trust roots; if the trust root has rotated and the
review environment cannot validate the bundle, the auditor treats that as
"not yet independently verified," not as a pass.

## Failure Modes The Gate Must Reject

- Missing or wrong attestation schema version: fail closed and regenerate using
  the versioned Townlight Core schema.
- Wrong workflow identity: fail closed. Identity must be exact repo + exact
  `.github/workflows/release.yml` + exact `refs/tags/<tag>`.
- Workflow rename or migration: fail closed until the runbook, fixture suite,
  and expected identity are updated through review.
- Wrong OIDC issuer: fail closed unless the issuer is
  `https://token.actions.githubusercontent.com`.
- Artifact hash mismatch: fail closed and rebuild from the verified target
  commit before signing.
- Tag target mismatch: fail closed if the attestation subject does not match
  GitHub's tag ref, target commit, and target tree.
- Transparency-log unavailability: fail closed for release publication. For
  already-published releases, use the preserved cosign bundle and documented
  offline verification path.
- Sigstore/Fulcio trust-root rotation: fail closed until pinned trust-root
  material and the runbook are updated. Root rotation is expected over time,
  but it is not silently accepted.
- Bootstrap trust problem: auditors must know which Sigstore roots and cosign
  version were used. Release evidence bundles preserve those inputs so an
  offline reviewer can distinguish "signature invalid" from "reviewer lacks
  the required trust-root material."

## CivicCore v0.22.0 Historical Defect Statement

Historical pre-baseline artifact: `v0.22.0`

Defect an outside auditor can verify:

- GitHub tag ref `refs/tags/v0.22.0` points directly at commit
  `483a224aaf2ae08868bd4cd4caf842bfda97db94`.
- The target commit is GitHub-verified and uses key ID `B5690EEEBB952194`.
- The release tag is lightweight.
- Under the current trust model, that lightweight tag may remain a pointer, but
  v0.22.0 does not yet have a Sigstore-signed `release-attestation.json`.
- Therefore v0.22.0 is not yet attestation-verified.

Reproducer after the new model is active:

```bash
python scripts/verify-release-provenance.py v0.22.0 \
  --repo CivicSuite/civiccore \
  --attestation release-attestation.json \
  --bundle release-attestation.json.bundle \
  --artifacts-dir .
```

Expected current result until an authorized attestation is added:

```text
FAIL: Live release verification requires --attestation and --bundle under the Sigstore attestation provenance model.
```

This release is ledgered as pre-gate, no attestation, do not promote as
baseline in
[`docs/ops/civiccore-tier1-retrofit-ledger.md`](civiccore-tier1-retrofit-ledger.md).
Do not add attestation assets, edit release notes, delete, or recreate it
without explicit chat authorization for that specific release.

## v0.1.17 Correction Note

The first v0.1.17 correction was performed in good faith against an unachievable
target: "GitHub-verified signed annotated tag object." The auditor authorized
that target before confirming that GitHub can produce it. The correction
preserved an audit trail, but it did not establish the final provenance model.
Under this model, v0.1.17 should receive an additive Sigstore attestation and a
second release-note audit entry only after explicit per-release authorization.

This is not recorded as a swarm execution failure. It is recorded as a model
correction: the human-provided target was mutually unsatisfiable with the
available GitHub tooling and no-local-key constraint, and the swarm stopped
instead of inventing a false path.

## Historical Baseline

The strengthened gate surfaced an org-wide historical provenance baseline
problem during the synthetic development phase: all 119 checked historical
CivicSuite release tags failed under the earlier tag-signature bar, split
between lightweight tags and unsigned annotated tag objects. That finding is
now understood as evidence that GitHub-native tags cannot carry the trust
burden for CivicSuite.

Historical releases are disclosed honestly rather than mass-deleted. The new
baseline begins with releases that include Sigstore-signed release attestations
and exact workflow-identity verification commands.

## Maintainer Environment Hygiene

Maintainer desktops and cloud-synced folders are scratchpads, not audit
surfaces. Drafts, runbooks, schemas, fixture analyses, defect statements, and
other artifacts under audit review must live in a Townlight repository on a
branch and move through a verified PR before review. If an artifact is too
sensitive for a public repository, it must live in an appropriate private
organization repository with the same verified-merge discipline.

Do not store signing keys, sensitive seed data, realistic PII-shaped mock data,
or release evidence requiring custody controls in consumer cloud-sync folders.
Public documentation drafts are not sensitive, but the pattern is still a
hygiene signal.

Maintainer notes copied from auditor conversations are auditor input, not
auditor output. Auditor decisions become operative only when explicitly written
in the chat as directives, approvals, or authorizations. Code, PRs, fixtures,
and runbooks produced by the development swarm are separate artifact classes
and must preserve that distinction in the audit trail.

## PR Review Report Format

When reporting a PR for audit review, copy review-surface file paths verbatim
from `git diff --name-only` or `git show --name-only --format=` output. Do not
retype paths from memory. A mismatched path in a review report is an
audit-trail-integrity defect even when the underlying artifact is correct,
because it forces reviewers to spend evidence-gathering effort finding the
actual file.

## Historical Disclosure Publication

The historical provenance disclosure is operative policy as of 2026-05-05 and
lives at `docs/ops/historical-provenance.md`.

The policy names `civiccore v0.22.1`, released 2026-05-05 at 16:23:36Z, as the
first attested CivicCore baseline release and links the live release
attestation, CivicCore Tier 1 retrofit ledger, and CO-4 cross-module retrofit
report.

Do not change the baseline release, edit historical public release notes, or
publish new attestations for earlier releases unless a future release-class
authorization explicitly approves that additive evidence.
