# townlight_core — GitHub Discussions seed posts

Drafts for the initial Discussions categories on https://github.com/townlight/core/discussions. Edit inline before posting.

---

## Announcements: townlight_core v0.2.0 released — Phase 2 LLM module

townlight_core v0.2.0 ships the LLM module: provider abstraction, prompt-template engine + 3-step override resolver, model registry service, context utilities, and structured-output helper. The full public API surface is importable from `townlight_core.llm`.

**What's new since v0.1.0:**
- `townlight_core.llm.providers` — `LLMProvider` ABC, decorator registry, built-in Ollama/OpenAI/Anthropic + Pydantic config schemas + `build_provider` factory
- `townlight_core.llm.templates` — string.Template engine, 3-step override resolver (DB override → app code override → townlight_core default), `OVERRIDE_REGISTRY`
- `townlight_core.llm.registry` — `ModelRegistry` ORM, async service, FastAPI admin router
- `townlight_core.llm.context` — token-budget assembly, prompt-injection sanitization
- `townlight_core.llm.structured` — Pydantic-validated output with retry-on-malformed
- Migration `townlight_core_0002_llm` — `prompt_templates` schema evolution

**Install:** `pip install https://github.com/Townlight/townlight_core/releases/download/v0.2.0/townlight_core-0.2.0-py3-none-any.whl`

**Compatibility:** records-ai v1.4.0 consumes this release.

---

## Q&A: How do I use townlight_core in a new module?

Add the wheel pin to your `pyproject.toml` and consume the public API from `townlight_core.llm`:

```toml
dependencies = [
    "townlight_core @ https://github.com/Townlight/townlight_core/releases/download/v0.2.0/townlight_core-0.2.0-py3-none-any.whl",
]
```

Run townlight_core migrations as part of your alembic chain (records-ai's `backend/alembic/env.py` shows the pattern: subprocess-invoke `townlight_core.migrations.runner.upgrade_to_head()` before your own migrations run).

---

## Dev / Architecture: Provider registry decorator pattern

`townlight_core.llm.providers` uses an in-process decorator registry rather than setuptools entry-points. Trade-offs:

- **For** decorator: zero startup cost, no packaging metadata complexity, simple to reason about
- **Against** decorator: third-party providers require a consumer-side import to register
- **Future:** entry-points layer can be added additively in a later release if a real third-party provider ecosystem materializes (YAGNI today)

ADR-0004 §6 has the full rationale. Discussion welcome on whether/when entry-points discovery is worth adding.

---

## Ideas: Future townlight_core modules

What modules belong in townlight_core vs. in their own consumer repos?

Currently in townlight_core:
- migrations runner + idempotency guards
- shared declarative `Base`
- `llm.{providers,templates,registry,context,structured}`

Likely candidates for future townlight_core modules:
- shared notification / channel abstraction (multi-consumer relevance)
- shared connector framework (records-ai already has connectors; townlight_meetings will too)

Likely **not** townlight_core concerns:
- domain-specific workflows (FOIA exemptions, meeting agendas)
- consumer-specific frontends

---

## Compatibility: townlight_records v1.4.0 pairing

records-ai v1.4.0 (released 2026-04-25) is the first downstream release consuming townlight_core v0.2.0. Compatibility statement:

| townlight_core | townlight_records | Status |
|---|---|---|
| 0.2.0 | 1.4.0 | Supported |
| 0.1.0 | 1.3.0 | Supported (Phase 1) |
| 0.1.0 | < 1.3.0 | Not applicable (pre-extraction) |

Townlight umbrella tracks the matrix at https://github.com/townlight/townlight/blob/main/docs/compatibility/index.md.
