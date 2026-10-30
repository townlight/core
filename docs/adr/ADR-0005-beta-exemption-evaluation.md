# ADR-0005: shared deterministic exemption evaluation

Status: implemented in private 1.3.0.dev1 candidate, not released.
Date: 2026-10-27

The owner authorized the beta plan, including resuming deferred Core work. This partially supersedes ADR-0002 for deterministic evaluation. Records supplies authorized active rule rows and persists review flags; Core owns the existing PII pattern implementation and bounded regex/keyword matching. Records compatibility imports remain. No package imports Records from Core.

Invalid or expensive expressions raise RuleEvaluationError; Records returns an explicit incomplete-scan 422 and rolls back rather than reporting no matches. Grouped patterns return whole text matches, correcting the prior tuple result defect. Jurisdiction is explicit in the Core API. Built-in PII patterns are suggestions, not legal exemptions. Rule objects carry IDs and versions; existing Records flag storage still does not retain immutable version/citation snapshots. That work, reviewed jurisdiction bundles, legal-source citations and the shared LLM review entry point remain open. No 50-state completeness or city legal acceptance is claimed. Existing Records optional LLM behavior is unchanged and remains separately unverified.

Evidence: real private PostgreSQL and native Records HTTP scan; actual grouped rule and PII flag creation, repeat deduplication, role/department denials and invalid-pattern 422; eight existing Records detector tests and nine Core evaluation tests. These do not certify legal correctness. Published artifacts and installed applications remain untouched.
