# CO-9 Audit-Full Release Gate

Date: 2026-05-05.

Repo: `CivicSuite/civiccore`.

Audit mode: release-gate.

Auditor: Codex, no subagents.

Post-publication addendum: the `v1.0` GitHub release is now published at
[`civiccore v1.0`](https://github.com/CivicSuite/civiccore/releases/tag/v1.0).
The live tag target is `a699814c6b97ff3ef13ecd9f04b5f4a2d76f7438`, release
workflow run `25408733597` completed successfully, and the release page carries
the wheel, sdist, `SHA256SUMS.txt`, `release-attestation.json`, and
`release-attestation.json.bundle`. The release-prep sections below are kept as
the contemporaneous gate record; post-publication verification now closes the
former PR/main-CI and release-publication gaps.

## 1. Executive Audit

Scope: CivicCore local release-prep checkout for CO-9 v1.0, plus live GitHub
remote state. Post-publication addendum scope includes the merged `main`
source tree and live `v1.0` GitHub release.

Local-vs-live parity: checked before release-prep edits. Local `main`,
`origin/main`, and `origin/HEAD` matched
`a1c52c9ed9daab67e63f2b33955efd98d734617b`. Post-publication parity is the
merged `main` commit and `v1.0` target
`a699814c6b97ff3ef13ecd9f04b5f4a2d76f7438`.

Overall verdict: PASS for CivicCore `v1.0` publication posture. No open
Blocker or Critical findings remain. PR CI, main CI, release workflow,
publication, and post-publication release-asset checks are now complete.

Ship posture: proceed to PR, CI, merge, then authorized `v1.0` release-class
operation if GitHub checks remain green.

Severity summary counts: Blocker 0, Critical 0, Major 0, Minor 0, Nit 0. One
release-consistency issue was found and fixed during this audit: the Tier 1
live checker now permits post-baseline releases only when both attestation
assets are live.

Static audit confidence: High for the local CO-9 branch contents.

Runtime sign-off confidence: High after PR CI, main CI, tag workflow,
release publication, and local Windows/Git Bash release verification.

Top cross-cutting findings: none open.

CI/workflow posture: `.github/workflows/ci.yml`, `cleanroom.yml`,
`release-preflight.yml`, and `release.yml` are present. Local workflow parsing
tests pass. The release workflow builds, signs, verifies, uploads exact asset
paths, and now publishes notes with evidence-pack and provenance commands.

## 2. Audit Coverage Ledger

| Lane | Status | Evidence summary | Blocker |
|---|---|---|---|
| Remote parity | Checked | `origin` is `https://github.com/CivicSuite/civiccore.git`; pre-edit local main matched `origin/main` at `a1c52c9`. | None |
| Local-vs-live commit truth | Checked | Post-publication local `main`, `origin/main`, and `v1.0^{}` match `a699814c6b97ff3ef13ecd9f04b5f4a2d76f7438`. | None |
| CI/workflow presence | Checked | Four workflows present; workflow YAML parse test passes. | None |
| Windows install path | Checked | `bash scripts/verify-release.sh` built and installed `civiccore-1.0.0` in a fresh venv. | None |
| Linux or Unix install path | Checked | Git Bash path passed locally; GitHub Linux CI and release workflow completed successfully for `v1.0`. | None |
| Platform parity verdict | Checked | Local Windows verification and GitHub Linux CI/release verification are green for `v1.0`. | None |
| First boot | Checked | Library import smoke checks `civiccore.__version__ == "1.0.0"` and public helpers. | None |
| Required post-install steps | Checked | Docs describe wheel install plus SHA256/Sigstore verification; no app bootstrap required. | None |
| Migrations | Checked | Baseline idempotency tests and migration tests collected and passed in release verifier. | None |
| Seed/bootstrap requirements | Not applicable | CivicCore is a library with no seed data path. | None |
| Runtime dependency and model requirements | Checked | LLM provider tests are mocked; no live model pull at import. | None |
| First-boot dependency truth | Checked | README/manual identify CivicCore as a library, not an end-user app. | None |
| Secrets and credential handling | Checked | Remote URL carries no embedded token; security config validation tests pass. | None |
| Auth and session handling | Checked | Bearer/trusted-header auth tests passed. | None |
| Authorization and role boundaries | Checked | Role parsing, trusted proxy source checks, and optional auth helpers are tested. | None |
| Response-schema sensitive-data exposure | Checked | Public API tests and security tests cover exposed helper surface; no app responses ship. | None |
| Audit and compliance logging | Checked | Audit chain and persisted audit hash tests pass. | None |
| External and admin surfaces | Checked | CivicCore exposes library/admin router primitives only; no standalone public service. | None |
| Connector implementation completeness | Checked | Docs now distinguish shipped local/import/sync primitives from unshipped vendor adapters. | None |
| Connector docs truth | Checked | README/manual/docs index scoped vendor-specific adapters as unshipped. | None |
| Background jobs and schedulers | Checked | Scheduling helpers ship; scheduler runtime/task queue remain module-owned. | None |
| Frontend critical journeys | Checked | Static docs landing page rendered at desktop and mobile. | None |
| Loading states | Checked | Static page load completed with Playwright. | None |
| Empty states | Not applicable | Static page has no data-backed empty state. | None |
| Error states | Checked | Browser console and page error counts were zero. | None |
| Partial states | Not applicable | Static local HTML renders all sections. | None |
| Accessibility cues | Checked | Keyboard focus sample and contrast ratios recorded in browser QA. | None |
| Docs truthfulness | Checked | Version/install copy moved to v1.0; ingest docs drift fixed. | None |
| Version consistency | Checked | `pyproject.toml`, `civiccore.__version__`, smoke test, docs, and SBOM align on `1.0.0`/`v1.0`. | None |
| Release artifact consistency | Checked | Workflow expected assets are wheel, sdist, SHA256SUMS, attestation JSON, and bundle. | None |
| Test realism | Checked | 273 tests collected in the post-publication quality pause; release verifier runs full test suite, ruff, build, fresh install. | None |
| Runtime, build, and test verification | Checked | `VERIFY-RELEASE: PASSED`. | None |
| Browser verification | Checked | `docs/browser-qa-co9-v1-closeout-summary.md` PASS. | None |
| Prior audit or verification challenge | Checked | CO-8 pack, CO-7 freeze evidence, and Tier 1 live check were challenged. | None |

## 3. Claim Verification Matrix

| Claim | Source | Verdict | Evidence |
|---|---|---|---|
| CivicCore is a shared platform library, not an end-user app. | README, manual, docs index | True | No app boot path; import smoke only. |
| v1.0 is the downstream productization release. | README, docs index, closeout | True | Package version `1.0.0`; install URL uses `v1.0`. |
| v0.22.1 remains the first attested baseline. | Historical policy, ledger | True | Baseline tag and ledger unchanged. |
| Freeze tag is `civiccore-m1-freeze`. | CO-7 evidence, release list | True | Live release and live Tier 1 check verify attestation assets. |
| Final v1.0 SBOM is present. | CO-8 evidence pack | True | `sbom-v1.0-pip-inspect.json`; test verifies `civiccore` `1.0.0`. |
| Release workflow publishes exact asset paths. | `.github/workflows/release.yml` | True | Workflow test asserts no wildcard `release-assets/*` upload. |
| Release notes include auditor commands. | `.github/workflows/release.yml` | True | Test asserts evidence-pack and provenance command text. |
| Docs landing page install path is current. | `docs/index.html` | True | Browser QA copy checks passed. |
| Supported agenda connectors are local import contracts, not live adapters. | README, tests | True | Connector import/sync tests pass; docs scope vendor adapters as unshipped. |
| Auth helpers ship for bearer and trusted-header roles. | README, tests | True | `tests/test_auth_bearer.py` passed in release verifier. |
| No outbound default LLM calls at import. | tests | True | LLM public API and provider tests are mocked/no-live. |
| Test count claim for release gate. | verifier output | True | 273 tests collected in the post-publication quality pause; release verifier passed. |
| Prior CO-8 evidence pack remains self-verifying. | test suite | True | Manifest hashes, threat signature, SBOMs, and license manifest tests pass. |
| v1.0 release is published. | GitHub release page | True | Live release exists with wheel, sdist, SHA256SUMS, attestation JSON, and Sigstore bundle. |

## 4. What The Dev Team Needs To Do Now

Must fix before ship:

- None open.

Should fix this sprint:

- Completed after publication: PR CI, main CI, tag publication, and
  post-publication verification. Owner area: release. Evidence:
  `v1.0` release workflow `25408733597`, live release assets, and
  release-provenance verification commands in the release notes.

Can defer if consciously accepted:

- Add post-release ledger row for `v1.0` only if governance decides the Tier 1
  retrofit ledger should become an all-future-release ledger. The live checker
  now prevents false failures by validating post-baseline attestation assets.

## 5. Next-Sprint Watchlist

Architecture: Keep downstream modules pinned to `civiccore-m1-freeze` until
their compatibility matrices move deliberately.

Security and compliance debt: Preserve release bundles and trust-root context
for offline procurement review.

UX debt: Future docs pages should avoid long status paragraphs if the static
landing page becomes more app-like.

Docs debt: CivicClerk must reference the freeze tag and CO-8/CO-9 evidence pack
when its productization lane starts.

Install and bootstrap debt: Downstream modules need cleanroom harnesses pinned
to the freeze tag, not moving CivicCore main.

Test debt: Add downstream compatibility tests as soon as CivicClerk begins.

Operational and release debt: Keep post-publication release verification linked
from the release record for every future release.

## 6. Engineering Deep Dive

Verdict: PASS.

Strengths: The release gate exercises full tests, lint, version lockstep,
build, fresh-venv install, and release-provenance fixtures. The release workflow
separates preflight, build/attest/verify, and publication jobs.

Findings: none open.

Verification gaps: None for the shipped `v1.0` source tree; downstream
module compatibility remains tracked outside this CivicCore audit.

## 7. Security And Authorization Deep Dive

Verdict: PASS.

Strengths: Auth boundary tests cover bearer and trusted-header roles. Release
trust uses exact GitHub Actions OIDC identity, issuer, artifact hashes, target
commit, and target tree. The remote URL contains no credential-bearing token.

Findings: none open.

Verification gaps: None for CivicCore `v1.0`; the Sigstore bundle is published
with the GitHub release.

## 8. UI/UX Deep Dive

Verdict: PASS for the static documentation surface.

Strengths: Browser QA covered loading, success, empty/error/partial
applicability, desktop/mobile screenshots, keyboard focus, contrast, overflow,
console/page errors, and copy truth for the new v1.0 surface.

Findings: none open.

Verification gaps: None for this static page.

## 9. Product/PM Deep Dive

Verdict: PASS.

Strengths: The docs now distinguish the downstream productization release
(`v1.0`) from the first attested baseline (`v0.22.1`) and the freeze-line tag
(`civiccore-m1-freeze`). This avoids overstating historical releases.

Findings: none open.

Verification gaps: None for CivicCore `v1.0`; CivicClerk gating moved to its
own productization lane after the release went live.

## 10. Documentation Deep Dive

Verdict: PASS.

Strengths: README, text README, user manual, docs index, changelog, evidence
pack, closeout report, release workflow notes, and Tier 1 ledger docs were
updated together. The docs drift that described `civiccore.ingest` as entirely
unshipped was corrected.

Findings: none open.

Verification gaps: None for the release page notes; the published release links
the evidence pack, historical provenance policy, closeout report, and auditor
verification commands.

## 11. Install / Bootstrap / Seeding Deep Dive

Verdict: PASS.

Strengths: CivicCore has no seed/bootstrap path. The install path is a GitHub
release wheel; verifier built `civiccore-1.0.0`, installed it into a fresh venv,
and imported public helpers.

Findings: none open.

Verification gaps: None for release existence; published wheel install remains
available through the GitHub release URL.

## 12. Version And Release Consistency Deep Dive

Verdict: PASS.

Strengths: `pyproject.toml`, `civiccore/__init__.py`, smoke tests, README,
README.txt, manuals, docs landing page, changelog, and final SBOM agree on
package version `1.0.0` and release tag `v1.0`. Historical `v0.22.1` references
remain as baseline history, not current install copy.

Findings: none open.

Verification gaps: None for release asset naming; the live release contains the
expected wheel, sdist, SHA256SUMS, attestation JSON, and bundle.

## 13. Test Engineering Deep Dive

Verdict: PASS.

Strengths: 273 tests collected in the post-publication quality pause. New and updated tests cover evidence-pack
files, manifest hashes, threat-model signature, final v1.0 SBOM, release
workflow note content, smoke version, and live ledger parity rules.

Findings: none open.

Verification gaps: Mutation/adversarial downstream compatibility remains for
CivicClerk and CivicCode lanes, not CO-9 CivicCore release prep.

## 14. Runtime QA Deep Dive

Verdict: PASS for local runtime QA.

[AUDITOR-RUN]

- `python -m pytest tests/test_tier1_retrofit_ledger.py tests/test_co8_procurement_evidence_pack.py tests/test_github_workflows.py tests/test_smoke.py -q` -> 16 passed, 1 warning.
- `python -m ruff check ...` -> all checks passed.
- `python scripts/check-tier1-ledger.py --live` -> 25 historical tags ledgered; post-baseline `civiccore-m1-freeze` attestation assets verified live.
- `python -m pytest --collect-only -q` -> 273 tests collected.
- Browser QA summary -> PASS.
- `bash scripts/verify-release.sh` -> full test suite passed, ruff passed, version lockstep `1.0.0`, build passed, fresh venv install/import smoke passed, `VERIFY-RELEASE: PASSED`.

[DEV-REPORTED]

- CO-7 downstream temporary harnesses: CivicClerk 553 passed; CivicCode 162 passed.

Findings: none open.

Verification gaps: None for CivicCore `v1.0` release publication; downstream
module compatibility remains separate.

## 15. Cross-Cutting Synthesis

The dominant release risk was not code behavior; it was truth synchronization
across version surfaces, release docs, evidence packs, and future live checks.
The CO-9 branch addressed that by moving version truth to `1.0.0`, keeping
`v0.22.1` as a historical baseline, adding final SBOM evidence, linking the
closeout report, and making the Tier 1 live checker resilient to post-baseline
attested releases. The former release-publication gap is now closed by the
published `v1.0` release and its attestation assets.

## 16. Verification Gaps And Sign-Off Limits

| Gap | Why it remains | Exact closing check | Blocks sign-off? |
|---|---|---|---|
| Downstream module compatibility | CivicCore `v1.0` is published, but each module still owns its compatibility matrix and pin movement. | Run each downstream module's release gate after changing its CivicCore pin. | Limits downstream sign-off only. |
| Offline procurement reproduction | Local audit checked live metadata and local release verification; full offline cosign/SHA reproduction depends on the reviewer's environment. | Download release assets in a clean environment and run the release-note verification commands. | Confidence limit, not a CivicCore source blocker. |

Sign-off limit: this report began as a release-prep audit and now includes a
post-publication addendum. It signs off CivicCore `v1.0` publication posture,
while downstream module compatibility remains outside this report.
