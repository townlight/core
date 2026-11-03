"""Prompt template rendering using stdlib string.Template (PEP 292).

Per ADR-0004, townlight_core uses string.Template (NOT Jinja2 or str.format) because:
- $name / ${name} syntax does not collide with literal JSON braces in prompts
  that show JSON examples to the LLM.
- Stdlib only — no dep cost.
- Existing call sites use plain variable interpolation; loops/conditionals are
  not required. If they become required, revisit.
"""
from __future__ import annotations

import string
from dataclasses import dataclass

from townlight_core.llm.templates.exceptions import PromptTemplateRenderError
from townlight_core.llm.templates.models import PromptTemplate


@dataclass(frozen=True)
class RenderedPrompt:
    """Result of rendering a PromptTemplate.

    Attributes:
        system: Rendered system_prompt string.
        user: Rendered user_prompt_template string.
        template_name: The source template's logical name.
        consumer_app: The source template's consumer_app namespace.
        version: The source template's version number.
    """

    system: str
    user: str
    template_name: str
    consumer_app: str
    version: int


def render_template(
    template: PromptTemplate,
    variables: dict[str, str] | None = None,
) -> RenderedPrompt:
    """Render a PromptTemplate's system and user prompts via string.Template.

    Uses ``substitute`` (NOT safe_substitute) so missing variables raise a
    clear error rather than silently leaving $name unsubstituted.

    Args:
        template: PromptTemplate ORM row to render.
        variables: Variable name -> value mapping. Defaults to empty dict.

    Returns:
        RenderedPrompt with system/user strings and template metadata.

    Raises:
        PromptTemplateRenderError: If a variable referenced by the template
            (in either system_prompt or user_prompt_template) is missing from
            the variables dict. The error names the missing variable.
    """
    vars_dict: dict[str, str] = dict(variables or {})

    # Render system_prompt
    try:
        system_rendered = string.Template(template.system_prompt).substitute(vars_dict)
    except KeyError as e:
        missing = e.args[0] if e.args else "<unknown>"
        raise PromptTemplateRenderError(
            template_name=template.template_name,
            consumer_app=template.consumer_app,
            missing_variable=missing,
        ) from e

    # Render user_prompt_template
    try:
        user_rendered = string.Template(template.user_prompt_template).substitute(vars_dict)
    except KeyError as e:
        missing = e.args[0] if e.args else "<unknown>"
        raise PromptTemplateRenderError(
            template_name=template.template_name,
            consumer_app=template.consumer_app,
            missing_variable=missing,
        ) from e

    return RenderedPrompt(
        system=system_rendered,
        user=user_rendered,
        template_name=template.template_name,
        consumer_app=template.consumer_app,
        version=template.version,
    )


__all__ = ["RenderedPrompt", "render_template"]
