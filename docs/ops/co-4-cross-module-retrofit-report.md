# CO-4 Cross-Module Tier 1 Retrofit Report

Status: closed on 2026-05-05.

## Scope

CO-4 applied the Tier 1 historical-release retrofit policy to downstream
Townlight modules whose public releases predated the Townlight Core v0.22.1
Sigstore-attested baseline:

- `townlight/sunshine` release `v1.4.10`
- `townlight/meetings` release `v0.1.20`
- `townlight/ordinances` releases `v0.1.17` and `v0.1.18`

## Decision

Each target release is now recorded as
`pre_gate_no_attestation_do_not_promote` in its owning repository. No public
GitHub release notes, tags, or release assets were changed. The active
downstream dependency and install documentation now point to the first
Townlight Core attested baseline, `v0.22.1`.

This report is a Townlight Core closeout index for the merged downstream work. The
source of truth for each product's target release remains the ledger committed
in that product repository.

## Merged Work

| Repository | PR | Base | Merge commit | Scope |
| --- | --- | --- | --- | --- |
| `townlight/sunshine` | [#67](https://github.com/CivicSuite/civicrecords-ai/pull/67) | `master` | `3b1f38c3d88050c1cf299cf8254eedf65f58a52a` | Ledgered `v1.4.10`, updated current Townlight Core dependency/docs to `v0.22.1`, added browser QA evidence, and copied ledger evidence into the backend image so CI verifies it. |
| `townlight/meetings` | [#142](https://github.com/CivicSuite/civicclerk/pull/142) | `main` | `b068233e87608931ff9165fad435a10fbade24a8` | Ledgered `v0.1.20`, updated current Townlight Core dependency/docs/workflows/rehearsal health checks to `v0.22.1`, and refreshed browser QA evidence. |
| `townlight/ordinances` | [#47](https://github.com/CivicSuite/civiccode/pull/47) | `main` | `4450931de51c1173adcff91d47e5373382670d89` | Ledgered `v0.1.17` and `v0.1.18`, updated current Townlight Core dependency/docs/workflows to `v0.22.1`, and added browser QA evidence. |

## Evidence

Local verification before push:

- Townlight Records: `python scripts\check-tier1-ledger.py --live`; `python -m pytest backend\tests\test_co4_tier1_retrofit_ledger.py -q`; `docker compose build api`; `docker compose run --rm --no-deps api python -m pytest tests/test_co4_tier1_retrofit_ledger.py -q`; `bash scripts/verify-release.sh`.
- Townlight Meetings: `python scripts\check-tier1-ledger.py --live`; `python scripts\verify-browser-qa.py`; focused ledger/runtime/release tests; `bash scripts/verify-release.sh`.
- Townlight Code: `python scripts\check-tier1-ledger.py --live`; focused ledger/runtime tests; `bash scripts/verify-release.sh`.
- All three downstream repos passed `git diff --check` and the required six-documentation-artifact gate before push.

GitHub verification:

- Townlight Records PR #67: backend docker-compose pytest, frontend build/tests,
  T2C bootstrap-failure smoke test, and ruff passed in run
  `25400139933`.
- Townlight Meetings PR #142: `verify` passed in run `25399238669`.
- Townlight Code PR #47: `verify-docs` passed in run `25399238535`.

Browser QA evidence:

- Townlight Records: `docs/browser-qa-co4-tier1-ledger-desktop.png`,
  `docs/browser-qa-co4-tier1-ledger-mobile.png`, and
  `docs/browser-qa-co4-tier1-ledger-summary.md`.
- Townlight Meetings: `docs/browser-qa-co4-tier1-ledger-desktop.png`,
  `docs/browser-qa-co4-tier1-ledger-mobile.png`, and
  `docs/browser-qa-co4-tier1-ledger-summary.md`.
- Townlight Code: `docs/browser-qa-co4-tier1-ledger-desktop.png`,
  `docs/browser-qa-co4-tier1-ledger-mobile.png`, and
  `docs/browser-qa-co4-tier1-ledger-summary.md`.

## Artifact Policy

No release-class artifacts were created by CO-4. No historical public release
notes, tags, release assets, checksums, or attestations were edited. CO-4 only
adds repo-controlled ledgers, tests, documentation truth updates, browser QA
evidence, and dependency alignment to the Townlight Core `v0.22.1` attested
baseline.

## Closure

CO-4 is complete when this Townlight Core report is merged after Townlight Core's release
gate passes. There are no exceptions recorded for the downstream Tier 1 retrofit
set.
