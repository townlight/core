<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# `civiccore.scaffold`

The generator that turns one validated module id into a working Townlight module skeleton.
ADR-0007 records the contract; ADR-0003 remains the historical deferral.

## What it writes

| Path (inside the new project directory) | Purpose |
| --- | --- |
| `pyproject.toml` | AGPL-3.0-only module package with a `civiccore>=` floor. |
| `src/<package>/manifest.json` | Validates through `civiccore.platform.ModuleManifest`. |
| `src/<package>/manifest.py` | `load_manifest()` — typed access, validated on load. |
| `src/<package>/app.py` | Minimal FastAPI staff surface using Core bearer auth. |
| `migrations/env.py` | Alembic env owning only the module schema; creates the schema before configuring the context. |
| `migrations/versions/<rev>_0001_baseline.py` | Additive baseline; `down_revision = None`; downgrade drops only the tables it created. |
| `tests/test_<package>_contract.py` | Manifest, fail-closed auth and admitted-role checks. |
| `docs/module.md`, `README.md`, `.gitignore` | The module contract, auth and migration rules. |

## CLI

```
python -m civiccore.scaffold plan  notes --name "Notes" --description "..."      # JSON plan
python -m civiccore.scaffold generate notes --name "Notes" --description "..." --target ./modules
```

`generate` refuses an existing directory, an unsafe module id, or a non-directory target and
exits `2` with a `refused: ...` line on stderr. `--dry-run` prints the plan and writes nothing.

## What the generated app does about credentials

Nothing is generated. The staff surface returns **503** until the operator sets
`<PACKAGE>_TOKEN_ROLES` to a JSON object mapping tokens to roles, **401** for a missing or
unknown token, and **200** only for a configured role. This is Core's shipped
`authorize_bearer_roles` behaviour, reused rather than reimplemented — there is no default
token and no insecure fallback.

## Verified on a real database

`work/beta-foundations/scaffold-01/pg-acceptance/harness.py` starts one disposable, owned
PostgreSQL 17 cluster, applies Core's real chain with
`civiccore.migrations.runner.upgrade_to_head` (head `civiccore_0006_rule_history`), then runs
the generated module's own chain from `migrations/`. It asserts the module stamps
`civicnotes_0001_baseline`, creates only schema `civicnotes`, leaves every Core table and the
Core revision untouched, is idempotent on re-run, survives a cluster stop/start, and
downgrades and re-upgrades cleanly. The cluster is stopped and deleted by the same process.
Receipts: `outputs/beta-plan/core-scaffold-01/pg-acceptance.json`.

That run found and fixed two template defects: `env.py` configured Alembic's version table
inside a schema that did not exist yet (`InvalidSchemaName`), and the baseline downgrade
dropped the schema that still held Alembic's version table (`DependentObjectsStillExist`).

## What deliberately is not here

No installer, no service registration, no umbrella host, no module registry writer, no settings
UI, no generated CI workflow and no release of this namespace. Generated modules still need the
umbrella owner to install and supervise them.
