# civiccore — GitHub Discussions seed posts

Drafts for the initial Discussions categories on https://github.com/townlight/core/discussions. Edit inline before posting.

---

## Announcements: civiccore v0.2.0 released — Phase 2 LLM module

civiccore v0.2.0 ships the LLM module: provider abstraction, prompt-template engine + 3-step override resolver, model registry service, context utilities, and structured-output helper. The full public API surface is importable from `civiccore.llm`.

**What's new since v0.1.0:**
- `civiccore.llm.providers` — `LLMProvider` ABC, decorator registry, built-in Ollama/OpenAI/Anthropic + Pydantic config schemas + `build_provider` factory
- `civiccore.llm.templates` — string.Template engine, 3-step override resolver (DB override → app code override → civiccore default), `OVERRIDE_REGISTRY`
- `civiccore.llm.registry` — `ModelRegistry` ORM, async service, FastAPI admin router
- `civiccore.llm.context` — token-budget assembly, prompt-injection sanitization
- `civiccore.llm.structured` — Pydantic-validated output with retry-on-malformed
- Migration `civiccore_0002_llm` — `prompt_templates` schema evolution

**Install:** `pip install https://github.com/CivicSuite/civiccore/releases/download/v0.2.0/civiccore-0.2.0-py3-none-any.whl`

**Compatibility:** records-ai v1.4.0 consumes this release.

---

## Q&A: How do I use civiccore in a new module?

Add the wheel pin to your `pyproject.toml` and consume the public API from `civiccore.llm`:

```toml
dependencies = [
    "civiccore @ https://github.com/CivicSuite/civiccore/releases/download/v0.2.0/civiccore-0.2.0-py3-none-any.whl",
]
```

Run civiccore migrations as part of your alembic chain (records-ai's `backend/alembic/env.py` shows the pattern: subprocess-invoke `civiccore.migrations.runner.upgrade_to_head()` before your own migrations run).

---

## Dev / Architecture: Provider registry decorator pattern

`civiccore.llm.providers` uses an in-process decorator registry rather than setuptools entry-points. Trade-offs:

- **For** decorator: zero startup cost, no packaging metadata complexity, simple to reason about
- **Against** decorator: third-party providers require a consumer-side import to register
- **Future:** entry-points layer can be added additively in a later release if a real third-party provider ecosystem materializes (YAGNI today)

ADR-0004 §6 has the full rationale. Discussion welcome on whether/when entry-points discovery is worth adding.

---

## Ideas: Future civiccore modules

What modules belong in civiccore vs. in their own consumer repos?

Currently in civiccore:
- migrations runner + idempotency guards
- shared declarative `Base`
- `llm.{providers,templates,registry,context,structured}`

Likely candidates for future civiccore modules:
- shared notification / channel abstraction (multi-consumer relevance)
- shared connector framework (records-ai already has connectors; civicclerk will too)

Likely **not** civiccore concerns:
- domain-specific workflows (FOIA exemptions, meeting agendas)
- consumer-specific frontends

---

## Compatibility: civicrecords-ai v1.4.0 pairing

records-ai v1.4.0 (released 2026-04-25) is the first downstream release consuming civiccore v0.2.0. Compatibility statement:

| civiccore | civicrecords-ai | Status |
|---|---|---|
| 0.2.0 | 1.4.0 | Supported |
| 0.1.0 | 1.3.0 | Supported (Phase 1) |
| 0.1.0 | < 1.3.0 | Not applicable (pre-extraction) |

Townlight umbrella tracks the matrix at https://github.com/townlight/townlight/blob/main/docs/compatibility/index.md.
