# Shared systems catalog candidate

`civiccore.catalog` provides async `domains(session)`, `system_catalog(session, domain=None)`, `connectors_for(session, domain)` and `import_catalog(session, payload, actor_id=...)`. The caller supplies its authenticated SQLAlchemy session and commits or rolls back. Core does not authenticate arbitrary callers or make vendor connections.

Apply Core migrations before using the new candidate. Existing `system_catalog`/`connector_templates` tables retain their data and shape. The new `civiccore_catalog_imports` ledger records complete imports and their SHA-256, actor, count and time. Reusing a version with changed or incomplete contents raises `ValueError`; nothing is silently replaced. Unknown domains return empty results. Connector templates are distinguished from commissioned connections.

Records' catalog routes and loader delegate to this contract, retaining staff/admin authorization. The reference catalog is shared non-secret product metadata; it does not contain municipal documents or serve as an authorization filter for search. Department-bound search remains another C1 requirement.

The current systems listing retains historical versions to preserve the existing Records API behavior. A version-selection UI, city-specific commissioning and general catalog administration remain outstanding. Installed-module inventory and recommendations are a separate contract in `civiccore.platform.inventory`—see [module-inventory.md](module-inventory.md) and [ADR-0008](adr/ADR-0008-beta-module-inventory.md)—and are deliberately not derived from catalog rows: reference data about vendor systems is not evidence that a module is installed. The broader `civiccore.catalog` promise is therefore not yet complete.
