# CivicCore Architecture Decision Records

CivicCore ADRs record module-scoped platform decisions. Cross-module decisions
that bind more than one repository remain in the umbrella `CivicSuite`
architecture ADR index.

## Placeholder Namespace Deferrals

These CO-7 ADRs define the placeholder namespace boundary for the freeze line:

- [ADR-0001: Defer `civiccore.catalog`](ADR-0001-defer-civiccore-catalog.md)
- [ADR-0002: Defer `civiccore.exemptions`](ADR-0002-defer-civiccore-exemptions.md)
- [ADR-0003: Defer `civiccore.scaffold`](ADR-0003-defer-civiccore-scaffold.md)

Rule: no downstream module may import, foreign-key to, document as required, or
otherwise depend on a placeholder namespace until that namespace ships in a
versioned CivicCore release artifact and the downstream compatibility matrix is
updated to name that release.

- [ADR-0004: Beta shared catalog extraction](ADR-0004-beta-shared-catalog.md) partially supersedes ADR-0001 in the private candidate; broader inventory remains open.

- [ADR-0005: Beta exemption evaluation](ADR-0005-beta-exemption-evaluation.md) partially supersedes ADR-0002 for the tested deterministic consumer.

- [ADR-0006: Immutable cited rule-version history](ADR-0006-rule-version-history.md) adds append-only citation/version retention around the ADR-0005 evaluator; reviewed real-city bundles, citation rendering in disclosure packets and consumer wiring remain open.

- [ADR-0007: Beta module scaffold](ADR-0007-beta-module-scaffold.md) partially supersedes ADR-0003 in the private candidate: a working one-project generator conforming to the existing manifest/auth/migration contracts. The ADR-0003 downstream consumption rule still applies because this candidate is not released; installer/umbrella registration and a generated per-module PostgreSQL integration test remain open. The existing generated project has been migrated on a disposable synthetic cluster (`work/beta-foundations/scaffold-01/pg-acceptance/`).

- [ADR-0008: Beta installed-module inventory and recommendations](ADR-0008-beta-module-inventory.md) partially supersedes ADR-0001/ADR-0004 for the tested persisted, scoped module inventory and its deterministic recommendations. It reuses the shipped `build_module_registry` rather than adding a resolver, records only caller-declared installs, and keeps the municipal systems catalog distinct. Per-city module commissioning, installer/umbrella registration, artifact proof and consumer wiring remain open.

- [ADR-0009: Department-scoped shared authority](ADR-0009-department-scoped-authority.md) adds the deny-by-default department/tenant authorization contract around the shipped auth, search, export and model-context helpers: a department claim is admissible only from the persisted `civiccore_department_grant_events` ledger, roles are intersected rather than unioned, revocation is an appended event, and no credential verifier, route or second permission engine is added. A Core HTTP/CLI surface, per-city department commissioning, role-to-job-function mapping and consumer wiring remain open.

- [ADR-0010: Claim-bound acceptance of ingest and media artifacts](ADR-0010-claim-bound-artifacts.md) adds one adapter (`civiccore.tasks.artifacts`, migration `civiccore_0009_job_artifacts`) that binds a derived artifact to the producing job identity and its still-active claim, publishes it only inside a configured store root with a re-verified sha256, and records an attributed, append-only receipt. It adds no transcription, OCR, transcoding, embedding, provider call or second job engine; consumer wiring, large-original storage and retention/redaction workflows remain open.
