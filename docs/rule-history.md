# Immutable cited rule versions

`exemption_rules` holds a consumer's *working* rules. It can be edited, disabled or
renumbered, so it cannot prove which cited text produced a past suggestion. Core therefore
keeps a separate append-only history in `civiccore_rule_versions`, added by
`civiccore_0006_rule_history`. See [ADR-0006](adr/ADR-0006-rule-version-history.md).

Apply Core migrations through `civiccore_0006_rule_history`. The migration is additive: no
existing table, row or column is altered, so a consumer that never calls the history API keeps
its current behaviour.

## Writing

```python
from civiccore.exemptions.history import record_rule_version

outcome = await record_rule_version(
    session,
    {
        "rule_id": rule_id,                 # same logical id as the working row
        "state_code": "CO",
        "version": 3,
        "category": "Personnel records",
        "rule_type": "keyword",            # only regex and keyword are admissible
        "rule_definition": "confidential, personnel file",
        "citation_text": "<reviewed citation text>",
        "citation_url": "https://example.invalid/...",
        "effective_from": date(2026, 1, 1),
        "retrieved_at": retrieved_at,       # timezone-aware
        "coverage_declaration": "tenant-supplied",
    },
    recorded_by="authenticated-staff-id",
    expected_current_version=2,            # compare-and-append; 0 means "no history yet"
)
await session.commit()                     # the caller owns the transaction
```

`recorded_by` is a caller-supplied authenticated identity. Core does not authenticate; the
application must authorize the write and must be truthful about the citation.

Refusals are exceptions, never silent overwrites:

| condition | result |
| --- | --- |
| exact repeat of a stored version | `inserted=False`, original row and recorder preserved |
| different definition/citation for a stored version | `RuleVersionConflictError` |
| version below, or not exactly next after, the stored maximum | `StaleRuleVersionError` |
| `expected_current_version` no longer current | `StaleRuleVersionError` |
| rule id already bound to another jurisdiction | `JurisdictionConflictError` |
| `official-legal-coverage`, all-state or other coverage claim | validation error |
| invalid or runaway regex | validation error carrying `RuleEvaluationError` |

## Reading

`rule_version(session, rule_id, version, state_code=...)` returns that exact persisted
version or `None`. `current_rule_version` returns the highest stored version.
`rule_history` returns the whole cited history oldest-first (`[]` when unknown).
All three are jurisdiction-scoped and raise `JurisdictionConflictError` rather than leaking a
row that belongs to another jurisdiction. Retrieval never falls back to the working table, so
an edited working row cannot masquerade as a cited version.

`current_rules(session, state_code, rule_ids=None)` returns only the latest version of each
rule as `civiccore.exemptions.Rule`, ordered by `(category, rule_id)`, ready for
`civiccore.exemptions.evaluate`. A superseded definition is never evaluated as current.

## Database guarantees

Triggers refuse UPDATE and DELETE on `civiccore_rule_versions`, and refuse an insert that
binds an existing rule id to a second jurisdiction. Rollback of the migration is a no-op on
purpose: deleting cited history would destroy provenance. Recover through backup/restore.

## Limits

This stores what an authorized caller reviewed and cited. It does not verify that a citation
is legally correct, that a jurisdiction's rules are complete, or that a suggestion is a
disclosure decision. Built-in PII patterns remain non-legal suggestions. Reviewed real-city
rule bundles, citation rendering in disclosure packets, a Core HTTP surface, and Records
wiring during its own scans remain open.
