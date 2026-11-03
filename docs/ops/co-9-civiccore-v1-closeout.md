<a id="co-9-civiccore-v10-closeout-report"></a>

# CO-9 Townlight Core v1.0 Closeout Report

Status: CO-9 release-gate closeout packet.

Date: 2026-05-05.

Repository: `townlight/core`.

Release tag: `v1.0`.

Python package version: `1.0.0`.

## Release Authorization Record

The release-class operation is covered by explicit chat authorization for:

| Sprint | Authorized operation | Scope |
|---|---|---|
| CO-2c | Cut Townlight Core `v0.22.1` | First Sigstore-attested baseline release. |
| CO-7 | Cut `civiccore-m1-freeze` | Freeze-line release for downstream module pins. |
| CO-9 | Cut Townlight Core `v1.0` | Downstream productization release. |

The CO-9 release payload is:

| Field | Value |
|---|---|
| Sprint ID | CO-9 |
| Repo | `townlight/core` |
| Target SHA | The GitHub-merged CO-9 release-prep commit on `main` |
| Tag / release name | `v1.0` / `civiccore v1.0` |
| Package version | `1.0.0` |
| Release assets | `civiccore-1.0.0-py3-none-any.whl`, `civiccore-1.0.0.tar.gz`, `SHA256SUMS.txt`, `release-attestation.json`, `release-attestation.json.bundle` |
| Auditor verification command | `python scripts/verify-release-provenance.py v1.0 --repo CivicSuite/civiccore --attestation release-attestation.json --bundle release-attestation.json.bundle --artifacts-dir .` |
| Expected Sigstore identity | `https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/v1.0` |
| Expected Sigstore issuer | `https://token.actions.githubusercontent.com` |
| Failure plan | If tag creation succeeds but release publication fails, stop release work, file a failure report, and do not delete, move, edit, or republish any public artifact without fresh release-class authorization. |

## Attested Releases

| Release | Role | Verification surface |
|---|---|---|
| [`v0.22.1`](https://github.com/CivicSuite/civiccore/releases/tag/v0.22.1) | First Sigstore-attested baseline release. | `release-attestation.json`, `release-attestation.json.bundle`, `SHA256SUMS.txt`, historical-provenance policy. |
| [`civiccore-m1-freeze`](https://github.com/CivicSuite/civiccore/releases/tag/civiccore-m1-freeze) | CO-7 downstream freeze-line release. | Freeze workflow run `25405991283`, target commit `3c4c34ccd153eeae705a57139f6713c356328b6d`, target tree `1e92d8b900b3d0134c4e8bc5b9133becff7822e6`. |
| [`v1.0`](https://github.com/CivicSuite/civiccore/releases/tag/v1.0) | CO-9 downstream productization release. | Release workflow, final SBOM, release attestation, SHA256SUMS, and post-publication provenance verification. |

## Retrofit Decisions

| Decision | Record |
|---|---|
| Historical release tags are preserved, not rewritten. | [`historical-provenance.md`](historical-provenance.md). |
| `v0.22.1` is the first attested baseline; older releases remain historical. | [`civiccore-tier1-retrofit-ledger.md`](civiccore-tier1-retrofit-ledger.md). |
| Cross-module historical retrofit findings are repo-controlled evidence, not desktop-only notes. | [`co-4-cross-module-retrofit-report.md`](co-4-cross-module-retrofit-report.md). |
| Future release trust is Sigstore attestation plus artifact hashes, not the GitHub "Verified" badge alone. | [`release-signing.md`](release-signing.md). |

## Spec Drift And ADR Record

| Surface | Resolution |
|---|---|
| Placeholder namespaces `civiccore.catalog`, `civiccore.exemptions`, and `civiccore.scaffold`. | ADR-deferred with downstream no-dependency rule in [`../adr/index.md`](../adr/index.md). |
| Historical release provenance drift. | Disclosed and governed by [`historical-provenance.md`](historical-provenance.md). |
| Downstream module freeze dependency. | `civiccore-m1-freeze` is the freeze-line tag; Townlight Meetings and Townlight Code productization lanes pin to the freeze, not moving `main`. |
| Procurement evidence gap. | CO-8 evidence pack plus CO-9 final SBOM. |

## Evidence Anchors

| Evidence | Location |
|---|---|
| CO-8 procurement pack | [`../evidence/co8-civiccore-procurement-evidence-pack/index.md`](../evidence/co8-civiccore-procurement-evidence-pack/index.md) |
| Final v1.0 SBOM | [`../evidence/co8-civiccore-procurement-evidence-pack/sbom-v1.0-pip-inspect.json`](../evidence/co8-civiccore-procurement-evidence-pack/sbom-v1.0-pip-inspect.json) |
| Cleanroom harness | [`cleanroom-harness.md`](cleanroom-harness.md) |
| CO-9 audit-full release gate | [`co-9-audit-full-release-gate.md`](co-9-audit-full-release-gate.md) |
| Release signing runbook | [`release-signing.md`](release-signing.md) |
| Historical provenance policy | [`historical-provenance.md`](historical-provenance.md) |
| Tier 1 retrofit ledger | [`civiccore-tier1-retrofit-ledger.md`](civiccore-tier1-retrofit-ledger.md) |

## Verification Gate

The CO-9 branch must pass these gates before tag publication:

1. `python -m pytest tests/test_co8_procurement_evidence_pack.py tests/test_github_workflows.py tests/test_smoke.py -q`
2. `python -m ruff check .`
3. `python -m pytest --collect-only -q`
4. Browser QA for `docs/index.html` at desktop and mobile widths because the docs landing page changes.
5. `bash scripts/verify-release.sh`
6. Release-gate audit-full with no Blocker or Critical findings.
7. GitHub PR CI on the CO-9 release-prep branch.
8. GitHub main CI after merge.

The tag push then runs the release workflow, which rebuilds artifacts, creates
`SHA256SUMS.txt`, signs `release-attestation.json`, verifies provenance before
publication, and publishes the GitHub release.

<a id="civicclerk-unblock-rule"></a>

## Townlight Meetings Unblock Rule

Townlight Meetings productization starts only after:

- `v1.0` is published,
- the release attestation verifies,
- `SHA256SUMS.txt` verifies,
- the final SBOM is present in the evidence pack,
- audit-full has no Blocker or Critical findings, and
- the release closeout is linked from the PR or release record.
