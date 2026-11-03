<a id="co-7-civiccore-freeze-readiness"></a>

# CO-7 Townlight Core Freeze Readiness

Status: pre-freeze evidence, release-class freeze tag not yet cut
Date: 2026-05-05

## Preflight

- Townlight Core local branch at sprint start: `main`
- Townlight Core origin/main and local HEAD: `fed0639cf66a5a155659bd2eff5bca4b282d600c`
- Townlight Core latest public release: `v0.22.1`, published 2026-05-05T16:23:36Z
- Townlight Core open PRs at sprint start: none
- Umbrella Townlight local branch at sprint start: `main`
- Umbrella origin/main and local HEAD: `e737648d6b9b286968f44b466098140dee83c868`
- Umbrella open PRs at sprint start: none
- Frontend changes in this sprint: docs index only; browser QA required before merge
- Release-class operations in this sprint: the freeze tag plus Sigstore
  attestation. This report does not publish that tag.

Tracked files were clean in both repos. Untracked scratch evidence from prior
browser and cleanroom runs was present and intentionally left uncommitted.

## Spec Lockstep

CO-7 reconciles the shipped Townlight Core surface against Townlight unified spec
section 6 and the Townlight Core README. The shipped freeze candidate includes:

- migrations and shared SQLAlchemy `Base`
- `civiccore.llm` provider, template, registry, context, and structured-output helpers
- audit, persisted audit-log verification, provenance, manifest, and export-bundle primitives
- city profile models and onboarding profile interview helpers
- auth helpers for bearer roles and trusted-header proxy boundaries
- local connector import normalization, delta planning, retry/circuit-breaker, and source-list status projection
- ingest discovery/fetch contracts and cited-source validation
- search normalization, deterministic text matching, access checks, and reciprocal-rank fusion
- notice deadline and compliance helpers
- cron schedule validation and next-run helpers
- connector host validation, startup config validation, encrypted JSON envelope helpers, and release-provenance verification

The umbrella spec and compatibility matrix are updated in the companion CO-7
Townlight PR so those shipped surfaces no longer appear as silent drift.

## Placeholder ADRs

The three README-listed placeholder namespaces now have Townlight Core ADRs:

- `docs/adr/ADR-0001-defer-civiccore-catalog.md`
- `docs/adr/ADR-0002-defer-civiccore-exemptions.md`
- `docs/adr/ADR-0003-defer-civiccore-scaffold.md`

Each ADR names the deferral rationale, target phase, and downstream consumption
rule: no module depends on the placeholder namespace until it ships in a
versioned Townlight Core release artifact.

## Downstream Placeholder Audit

Local command:

```powershell
git -C <module> grep -n -E 'civiccore\.(catalog|exemptions|scaffold)|from civiccore import (catalog|exemptions|scaffold)|import civiccore\.(catalog|exemptions|scaffold)' -- .
```

Result: no production-code reliance found across the compatibility-matrix module
set. Townlight Meetings and Townlight Code contain test-only references to
`civiccore.exemptions` and `civiccore.catalog` inside guard tests that assert
module schemas do not foreign-key into unreleased Townlight Core placeholder targets.

A production-code-only sweep excluding tests returned clean for every module in
the compatibility matrix.

## Verification Log

Local checks completed on 2026-05-05 before any freeze tag publication:

- `python -m pytest tests/test_placeholder_adrs.py -q`: 3 passed.
- `python -m ruff check tests/test_placeholder_adrs.py civiccore/catalog/__init__.py civiccore/exemptions/__init__.py civiccore/scaffold/__init__.py`: passed.
- `python -m pytest --collect-only -q`: 260 tests collected.
- `bash scripts/verify-release.sh`: passed, including 260 tests, Ruff, docs
  checks, build artifacts, and fresh virtualenv import/version smoke.
- `git diff --check`: passed.
- Browser QA for this repo:
  `docs/browser-qa-co7-placeholder-adrs-summary.md` passed with desktop
  1280x900 and mobile 390x844 screenshots, zero browser console messages, zero
  page errors, no horizontal overflow, keyboard focus proof, contrast proof,
  and copy review.
- Companion Townlight docs verification:
  `bash scripts/verify-docs.sh` passed.
- Companion Townlight suite-state verification:
  `python scripts/verify-suite-state.py --remote-only` passed for all 26 repos
  and confirmed `civiccore 0.22.1`.
- Companion Townlight browser QA:
  `docs/browser-qa-co7-civiccore-freeze-lockstep-summary.md` passed with
  desktop 1280x900 and mobile 390x844 screenshots, zero browser console
  messages, zero page errors, no horizontal overflow, keyboard focus proof,
  contrast proof, and copy review.

## Freeze Boundary

The release-class freeze tag remains pending. Before publication, the release
payload must name the target SHA, freeze tag, exact attestation command,
expected OIDC identity and issuer, SHA256SUMS verification path, and fix-forward
plan.
