# ADR-0004: Resume shared catalog extraction for the beta candidate

Status: Implemented in the private beta candidate; release and broad catalog acceptance pending
Date: 2026-10-27
Supersedes: ADR-0001 only for the tested systems-catalog extraction below

The owner approved completing the nine-product beta plan. Records already contains a real systems catalog and authenticated routes; implementing a second catalog would create two authorities. Core now owns validated versioned imports, domain/system reads and connector-template discovery over the existing shared tables. Records retains its authentication and delegates to this library. Caller transactions and commit ownership remain explicit.

A new Core migration adds an import ledger with source hash, row count, actor and time. Imports are serialized and immutable by version. Pre-extraction rows are adopted only when the complete row set matches; a changed or partial version is rejected without overwriting evidence. Catalog entries are reference data, not confirmation that a vendor is connected. Connector results explicitly say template-only. No runtime network discovery or credentials are introduced.

This does not complete installed-module inventory, recommendations, shared exemption rules or scaffolding. Those clauses remain open in the beta acceptance register. Historical ADR-0001 remains preserved. Consumers of this candidate must pair the new Core artifact and Records source; existing release pins remain intact until a coherent candidate is packaged and authorized for delivery.

Acceptance: actual PostgreSQL migration/import/concurrency tests and the Records HTTP consumer through the Windows native runtime, including denied public reads, denied staff import, unknown-domain empties and process-restart persistence. These are isolated candidate checks, not release or installed-city acceptance.
