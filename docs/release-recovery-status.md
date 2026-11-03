# CivicCore Release Recovery Status

Date: 2026-05-07
Repo: `CivicSuite/civiccore`

## v1.0.1 Recovery Patch

`v1.0.1` is the recovery patch for the post-`v1.0` main branch. It includes the
audit-finding fix and the provisional-status marking from the recovery range.

Security hardening: CivicCore auth errors no longer expose diagnostic role,
principal, caller-host, or trusted-proxy CIDR fields. The removed fields are
`token_roles`, `principal`, `principal_roles`, `client_host`, and
`trusted_proxy_cidrs`. The affected files are `civiccore/auth/bearer.py` and
`civiccore/auth/trusted_headers.py`. Rationale is recorded in
`docs/audits/civiccore-audit-full-2026-05-07.md`.

Operator note: if your monitoring or downstream tests assert these field names
in CivicCore auth error responses, update them before bumping the pin.

## Current Verdict

`v1.0.1` is the current recovery patch line. The original `v1.0` GitHub release
remains historical and should point operators to `v1.0.1`.

## Recovery Gates

| Gate | Current status | Evidence |
| --- | --- | --- |
| Public product-ready claim freeze | Passing | README, text README, user manual, docs landing page, and package classifier now avoid production/stable promotion. Claim scan only found negative/provisional wording. |
| Runtime install proof | Passing | `scripts/verify-release.sh` builds a wheel and installs it into a clean virtualenv. Verified in native WSL on 2026-05-07. |
| Native WSL/Linux proof | Passing | Release gate selected `.venv-wsl/bin/python3`, ran on Linux Python 3.12, collected 274 tests, and passed. |
| Security scan | Passing | Tracked-file secret scan found no matches outside ignored evidence/scratch surfaces. |
| Docs-source consistency | Passing | Version and release posture are tested from source files. |
| Mock-vs-production labeling | Passing for library scope | README and user manual distinguish shipped helpers from placeholders and unshipped platform behaviors. |
| Browser/user-flow QA | Passing | CivicCore is a library. Playwright checked the docs landing page at desktop and mobile widths, with no console/page errors, visible provisional copy, keyboard focus samples, and no horizontal overflow. |

## Sign-Off Boundary

CivicCore is a shared library, not an end-user municipal app. It cannot by
itself prove that a city can run the CivicSuite product family. Downstream
modules must re-earn their own release status with module-specific runtime,
UX, integration, security, and documentation gates.
