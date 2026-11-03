"""Exceptions raised by the prompt template engine and resolver."""
from __future__ import annotations


class PromptTemplateError(Exception):
    """Base class for prompt template errors."""


class PromptTemplateNotFoundError(PromptTemplateError):
    """Raised when no template matches the requested (consumer_app, template_name).

    The error message must direct the caller to either (a) seed the template
    in the prompt_templates table for the requesting consumer_app, or (b)
    create a townlight_core default. Both fields are exposed as attributes for
    programmatic inspection.
    """

    def __init__(self, *, template_name: str, consumer_app: str) -> None:
        self.template_name = template_name
        self.consumer_app = consumer_app
        super().__init__(
            f"No active prompt template found for "
            f"template_name={template_name!r}, consumer_app={consumer_app!r}. "
            f"Insert an active row into prompt_templates with either "
            f"consumer_app={consumer_app!r} (app override, is_override=true) or "
            f"consumer_app='townlight_core' (townlight_core default, is_override=false)."
        )


class PromptTemplateRenderError(PromptTemplateError):
    """Raised when string.Template substitution fails for a template.

    Most commonly: the caller's variables dict is missing a key referenced by
    the template body. The missing variable name is exposed as an attribute and
    named in the error message.
    """

    def __init__(
        self,
        *,
        template_name: str,
        consumer_app: str,
        missing_variable: str,
    ) -> None:
        self.template_name = template_name
        self.consumer_app = consumer_app
        self.missing_variable = missing_variable
        super().__init__(
            f"Failed to render prompt template "
            f"(template_name={template_name!r}, consumer_app={consumer_app!r}): "
            f"missing variable {missing_variable!r}. "
            f"Provide a value for {missing_variable!r} in the variables dict, "
            f"or update the template to drop the $${missing_variable} reference."
        )


__all__ = [
    "PromptTemplateError",
    "PromptTemplateNotFoundError",
    "PromptTemplateRenderError",
]
