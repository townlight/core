# ADR-0006: immutable, cited jurisdiction-rule version history

Status: implemented in private 1.3.0.dev1 candidate, not released.
Date: 2026-10-27

## Context

ADR-0005 shipped one deterministic evaluator (`civiccore.exemptions.evaluate`) and left
one named gap open: "existing Records flag storage still does not retain immutable
version/citation snapshots." A consumer could edit `exemption_rules.version` in place, so a
disclosure review could no longer prove which cited rule text produced a suggestion.

## Decision

Add `civiccore.exemptions.history` plus migration `civiccore_0006_rule_history`. A rule
version is an append-only row keyed by `(rule_id, version)` carrying the definition, rule
type, citation text, optional citation URL, effective date, retrieval timestamp, coverage
declaration, a SHA-256 fingerprint of the cited content, and the attributed recorder.

Deliberate boundaries:

* **No second rule engine.** `RuleVersion.as_rule()` returns the existing frozen
  `civiccore.exemptions.Rule`, so persisted history feeds the ADR-0005 evaluator unchanged.
  Pattern admission at write time calls the same shared scanner through the new
  `validate_rule_pattern()`, which exists because the evaluator is lazy: `finditer` on empty
  text never compiles, so a scan-only check accepted `"["`. That defect was found by the new
  test suite before this ADR was written.
* **No foreign key to `exemption_rules`.** That table stays the consumer's mutable working
  row. History must survive disabling or editing it. `rule_id` is the caller's same logical
  UUID, not a database reference.
* **No claim of legal coverage.** `coverage_declaration` is a closed set of
  `synthetic-fixture` and `tenant-supplied`. Core cannot store a row asserting official
  coverage, and nothing here says any jurisdiction's rules are complete.
* **Append-only in the database, not only in Python.** Triggers refuse UPDATE and DELETE and
  refuse binding one rule id to a second jurisdiction, so a caller that bypasses this module
  still cannot destroy cited provenance. Downgrade is a no-op: recover by restore.
* **Explicit stale/duplicate semantics.** An exact repeat of a stored version returns
  `inserted=False` and keeps the original recorder; changed content for a stored version
  raises `RuleVersionConflictError`; a lower or non-contiguous version, or a stale
  `expected_current_version` compare-and-append guard, raises `StaleRuleVersionError`;
  crossing jurisdictions raises `JurisdictionConflictError`.

## Consequences

Consumers must now append a version when a cited rule changes instead of mutating the working
row, and must supply a real citation text (synthetic fixtures must say they are synthetic).
Retrieval is deterministic: `rule_version`, `current_rule_version`, `rule_history` and
`current_rules` are ordered, jurisdiction-scoped and explicit about an unknown rule (empty or
`None`, never a fabricated default).

Still open, and not implied by this ADR: reviewed jurisdiction rule *bundles* for real cities,
legal-source verification, citation rendering in disclosure packets, a Core HTTP surface for
history, and Records wiring that appends history during its own scans. No 50-state coverage
and no city legal acceptance is claimed.

Evidence: `work/beta-foundations/rule-history-01/harness.py` on a disposable synthetic
PostgreSQL cluster (migration head `civiccore_0006_rule_history`, real append/conflict/stale/
duplicate/jurisdiction/concurrency behaviour and trigger-level refusal) plus
`tests/test_rule_version_history.py` contract tests and the existing exemption/placeholder
regressions. See `outputs/beta-plan/core-rule-history-01/`.
