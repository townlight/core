"""Townlight Core LLM prompt template ORM, schemas, rendering, and resolution.

Phase 2 Step 3a added: PromptTemplate ORM + Pydantic schemas.
Phase 2 Step 3c added: rendering (string.Template engine) + override resolution.
"""
from __future__ import annotations

# Side-effect import: ensure ModelRegistry is registered with civiccore.db.Base.metadata
# so SQLAlchemy can resolve PromptTemplate.model_id's FK("model_registry.id") at
# mapper configuration time. Without this, querying PromptTemplate from a session
# where only civiccore.llm.templates was imported raises NoReferencedTableError.
from civiccore.llm.registry.models import ModelRegistry  # noqa: F401

from civiccore.llm.templates.engine import RenderedPrompt, render_template
from civiccore.llm.templates.exceptions import (
    PromptTemplateError,
    PromptTemplateNotFoundError,
    PromptTemplateRenderError,
)
from civiccore.llm.templates.models import PromptTemplate
from civiccore.llm.templates.overrides import (
    OVERRIDE_REGISTRY,
    register_template_override,
    unregister_template_override,
)
from civiccore.llm.templates.resolver import CIVICCORE_DEFAULT_APP, resolve_template
from civiccore.llm.templates.schemas import (
    PromptTemplateCreate,
    PromptTemplateRead,
)

__all__ = [
    "OVERRIDE_REGISTRY",
    "register_template_override",
    "unregister_template_override",
    "PromptTemplate",
    "PromptTemplateCreate",
    "PromptTemplateRead",
    "RenderedPrompt",
    "render_template",
    "resolve_template",
    "CIVICCORE_DEFAULT_APP",
    "PromptTemplateError",
    "PromptTemplateNotFoundError",
    "PromptTemplateRenderError",
]
