<a id="contributing-to-civiccore"></a>

# Contributing to Townlight Core

Thanks for considering a contribution. Townlight Core is the shared platform
package for the [Townlight](https://github.com/townlight/townlight)
open-source municipal operations suite — every line of code here is
consumed by every Townlight module, so the bar is high and the surface
is deliberately small.

## Status

Townlight Core is at v0.1 (Phase 0 — package skeleton). Functional code lands
in Phase 1 and beyond per the Townlight Core Extraction Spec section 12. If
you want to contribute today, the most useful work is:

- Reviewing the Extraction Spec (in CivicSuite/civicsuite) and filing
  issues against ambiguous wording.
- Building a Phase 1 prototype against the auth + audit subsystem
  contracts in Appendix A of the spec.

---

## Where does my bug go? (decision tree)

Townlight is a multi-repo project. Filing a bug in the wrong place
delays the fix. This decision tree mirrors the one in every Townlight
repo's `CONTRIBUTING.md`, written here from Townlight Core's perspective. It
is a copy of the mitigation guidance from the Townlight Core Extraction Spec
section 18 ("Contributor confusion about where to file a bug").

1. **Is the bug in shared platform infrastructure?**
   That means: authentication, RBAC, the audit chain, LLM abstraction,
   document ingestion, hybrid search, the connector framework, the
   notification service, onboarding, the municipal systems catalog, the
   50-state exemption engine, sovereignty verification scripts, shared
   ORM models, or shared-table Alembic migrations.
   ➜ **File it here:** https://github.com/townlight/core/issues

2. **Is the bug in records-request workflow, response-letter generation,
   fee schedules, the records dashboards, or any records-specific UI
   page?**
   ➜ **File it in Townlight Records:**
   https://github.com/townlight/sunshine/issues

3. **Is the bug in meeting agendas, minutes, voting, or the clerk
   workflow?**
   ➜ **File it in Townlight Meetings** (when it exists). Until then, file it in
   the Townlight umbrella so we can route it.

4. **Is the bug about how the modules fit together, the suite-wide
   roadmap, the module catalog, or cross-module documentation?**
   ➜ **File it in the Townlight umbrella:**
   https://github.com/townlight/townlight/issues

5. **Are you reporting a security vulnerability?**
   Do not file it as a public issue. See "Security advisories" below.

If you are unsure — file it in the Townlight umbrella repo. A
maintainer will move it to the right place. Better here than
nowhere.

---

## Development setup

Requirements:

- Python `>=3.11` (Townlight Core widens past civicrecords-ai's 3.12 floor
  because it is a shared library).
- Git.
- A POSIX-ish shell or PowerShell. The package itself is OS-agnostic.

Clone and install in editable mode with the dev extras:

```bash
git clone https://github.com/CivicSuite/civiccore.git
cd civiccore
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -e .[dev]
```

Run the test suite:

```bash
pytest
```

Run the sovereignty verification scripts (Phase 4 will populate
`scripts/verify/`; today this directory is a placeholder):

```bash
bash scripts/verify/verify_no_egress.sh        # planned
python scripts/verify/verify_no_telemetry.py   # planned
```

---

## Code standards

- Match existing patterns. Where a pattern is missing, follow the
  conventions in `civicrecords-ai/backend/app/` — Townlight Core is being
  extracted from that codebase and consistency makes the migration
  reviewable.
- Type hints on every public function. `mypy` strictness ratchets up
  with each phase.
- `ruff` with the project config (`pyproject.toml`). Run `ruff check`
  and `ruff format` before submitting.
- Async/await consistently for any I/O path.
- No telemetry. No outbound network calls at runtime. Townlight Core inherits
  the Townlight sovereignty stance unmodified.

## Tests

Every change that modifies logic or a public interface must include or
update at least one automated test in `tests/`. Cosmetic-only changes
(comments, formatting, doc copy) are exempt. The test suite must work
from a clean clone with only the steps documented above — no hidden
state.

## Semantic versioning discipline

Per the Townlight Core Extraction Spec section 16, the public API surface
listed in Appendix A is stable across the v0.x series:

- **MAJOR** — any breaking change to the Appendix A surface (removed
  symbol, changed signature, changed behavior). Also: any schema change
  to a shared table.
- **MINOR** — new public symbols, new optional parameters, new
  backward-compatible behavior.
- **PATCH** — bug fixes that do not change the public API or shared
  schema.

When you bump the version, update it in every location in the same
commit (currently: `pyproject.toml` `[project].version` and
`civiccore/__init__.py` `__version__`).

## Security advisories

Do not file security issues as public GitHub issues. Use GitHub's
private vulnerability reporting on this repository (Security tab → Report
a vulnerability), or email the maintainer listed on the
[Townlight umbrella repo](https://github.com/townlight/townlight)
governance page. We will acknowledge within seven days and coordinate a
fix and disclosure timeline with you.

## License

By contributing, you agree your contribution is licensed under
AGPL-3.0-only;
documentation contributions are licensed under CC BY 4.0. See
[LICENSE](LICENSE).
