"""
Pydantic v2 schemas for prompt template create / read / update operations.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PromptTemplateCreate(BaseModel):
    """Fields required (or defaulted) when creating a new prompt template."""

    # Required
    template_name: str
    purpose: str
    system_prompt: str
    user_prompt_template: str

    # Optional with defaults
    consumer_app: str = "townlight_core"
    is_override: bool = False
    token_budget: dict | None = None
    model_id: int | None = None
    version: int = 1
    is_active: bool = True
    created_by: uuid.UUID | None = None


class PromptTemplateRead(BaseModel):
    """All columns for reading a prompt template row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_name: str
    consumer_app: str
    is_override: bool
    purpose: str
    system_prompt: str
    user_prompt_template: str
    token_budget: dict | None
    model_id: int | None
    version: int
    is_active: bool
    created_by: uuid.UUID | None
    created_at: datetime


class PromptTemplateUpdate(BaseModel):
    """Partial update schema for PATCH operations. All fields optional."""

    template_name: str | None = None
    purpose: str | None = None
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    consumer_app: str | None = None
    is_override: bool | None = None
    token_budget: dict | None = None
    model_id: int | None = None
    version: int | None = None
    is_active: bool | None = None


__all__ = ["PromptTemplateCreate", "PromptTemplateRead", "PromptTemplateUpdate"]
