# Persisted installed-module inventory and recommendations

Status: private beta candidate (Core 1.3.0.dev1 source). Not released, not installed, not
packaged. See [ADR-0008](adr/ADR-0008-beta-module-inventory.md) for the decision record and
`outputs/beta-plan/core-module-inventory-01/` for executed evidence.

`civiccore.platform.inventory` records what one deployment scope *declares* it has installed and
enabled, and derives deterministic suggestions from those declarations. It is the installed-module
half of CORE-08 / `C1.catalog.modules`.

## What this is not

* **Not a scan.** Nothing enumerates a machine, a package directory, a registry, a server or an
  endpoint. There is no network call anywhere in this module.
* **Not an installer.** No package is downloaded, installed, enabled, disabled, repaired or
  uninstalled here, and no runtime action is triggered.
* **Not the municipal systems catalog.** `civiccore.catalog` describes *vendor systems* (domains,
  vendors, protocol templates). This module describes *Townlight module packages*. A catalog row
  never implies a module is installed, and an inventory row never implies a vendor is connected.
  The two do not share tables or rows.
* **Not a second resolver.** Admission, minimum Core version, dependency minimums, transitive
  blocking and required cycles all come from
  `civiccore.platform.modules.build_module_registry`. This module only stores declarations and
  asks that resolver what they admit.
* **Not proof.** A recommendation is advice over declared metadata. It does not prove a package
  is present, running, healthy or licensed.

## Public surface

```python
from civiccore.platform import (
    ModuleInventory, ModuleInventoryEntry, ModuleRecommendation,
    record_inventory, current_inventory, inventory_revision, inventory_history,
    require_installed, module_recommendations,
    ModuleInventoryError, UnknownModuleError, StaleInventoryError, InventoryConflictError,
)
```

Import these from `civiccore.platform` (as with `civiccore.catalog` and
`civiccore.exemptions.history`), not from the package root.

### Declaring an inventory

```python
outcome = await record_inventory(
    session,
    ModuleInventory(
        scope_id="city-a",              # caller-supplied deployment scope
        revision=1,                    # next revision; append-only
        civiccore_version="1.3.0.dev1",
        entries=[ModuleInventoryEntry(module_id="records", version="1.8.0",
                                      enabled=True, manifest=manifest)],
    ),
    recorded_by="fixture-admin",       # attributed caller identity
    expected_revision=0,               # compare-and-append guard; 0 = "no inventory yet"
)
await session.commit()                 # the caller owns the transaction
```

Reads are `current_inventory(session, scope_id)`, `inventory_revision(session, scope_id,
revision)` and `inventory_history(session, scope_id)`.

### Deriving recommendations

```python
module_recommendations(inventory, available_manifests=[other_manifest])
```

`available_manifests` is what the caller states is present for that scope. Omitting it claims
no availability. Each `ModuleRecommendation` carries `module_id`, `action`, `basis`
(`installed` or `available`), `reasons` (resolver text or an explicit "dependencies are
declared and compatible"), and plain `operator_action` copy.

| `action` | Meaning |
| --- | --- |
| `install` | The package was handed in as available, is not declared installed, and every required dependency would be satisfied. |
| `enable` | Declared installed but switched off, and turning it on would be admitted. |
| `resolve-dependency` | A required module dependency is missing, below its minimum version, blocked, or cyclically required. |
| `upgrade-core` | The module needs a newer CivicCore than this deployment declares. |
| `not-supported` | The module does not support the declared install profile (e.g. `windows_local`). |

A module that is installed, enabled and admitted produces **no** recommendation. Silence is not
a claim of health.

Ordering is `(module_id, action)` and reasons come from the resolver, so identical inputs give
byte-identical output.

## Refusals

| Condition | Result |
| --- | --- |
| `recorded_by` blank or > 128 chars | `ModuleInventoryError` |
| `scope_id` not a lowercase 2–64 char identifier | `ModuleInventoryError` / pydantic `ValidationError` |
| Two entries for one `module_id` | `ValueError` |
| Entry `module_id`/`version` disagree with its manifest | `ValueError` |
| Exact repeat of the stored revision | `inserted=False`, original recorder kept |
| Same revision, different content | `InventoryConflictError` |
| Lower or backfilled revision | `StaleInventoryError` |
| Revision gap (`current+2`) | `StaleInventoryError` |
| `expected_revision` behind the stored maximum | `StaleInventoryError` |
| `expected_revision` negative | `ModuleInventoryError` |
| `require_installed` names an id the scope does not declare | `UnknownModuleError` |

PostgreSQL independently refuses `UPDATE`/`DELETE` on both inventory tables with a trigger, so
history cannot be rewritten even outside this library.

## Persistence

Migration `civiccore_0007_module_inventory` (down_revision `civiccore_0006_rule_history`) adds,
additively:

* `civiccore_module_inventory` — one row per `(scope_id, revision)`: profile, declared
  CivicCore version, content SHA-256, recorder, time.
* `civiccore_module_inventory_entries` — one row per declared module: version, enabled flag and
  the full manifest as `jsonb`, keyed `(scope_id, revision, module_id)` with a composite foreign
  key to the header.

Scope isolation is structural (composite keys and FK), not a uniqueness rule on `module_id`: the
same module package may legitimately be declared installed by two different deployment scopes.
Downgrade is a deliberate no-op — dropping the inventory would erase which modules a scope
declared installed, so recovery is restore-from-backup.

`scope_id` is supplied by the caller. Core never invents, enumerates or authenticates a scope,
and makes no claim that a declared scope exists.
