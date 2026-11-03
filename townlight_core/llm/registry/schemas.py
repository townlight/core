"""
Pydantic v2 schemas for the model_registry resource.

Three schemas cover the standard CRUD surface:

- ``ModelRegistryCreate``  — POST body (create a new model record).
- ``ModelRegistryRead``    — GET response (all fields, ORM-compatible).
- ``ModelRegistryUpdate``  — PATCH body (all fields optional, partial updates).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ModelRegistryCreate(BaseModel):
    """Schema for creating a new model_registry record (POST body)."""

    model_name: str
    model_version: str | None = None
    parameter_count: str | None = None
    license: str | None = None
    model_card_url: str | None = None
    is_active: bool = False
    context_window_size: int | None = None
    supports_ner: bool = False
    supports_vision: bool = False


class ModelRegistryRead(BaseModel):
    """Schema for returning a model_registry record (GET response).

    ``from_attributes=True`` allows construction directly from an ORM instance.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    model_version: str | None = None
    parameter_count: str | None = None
    license: str | None = None
    model_card_url: str | None = None
    is_active: bool
    added_at: datetime | None = None
    context_window_size: int | None = None
    supports_ner: bool
    supports_vision: bool


class ModelRegistryUpdate(BaseModel):
    """Schema for partially updating a model_registry record (PATCH body).

    Every field is optional so callers can send only the fields they want to
    change.
    """

    model_name: str | None = None
    model_version: str | None = None
    parameter_count: str | None = None
    license: str | None = None
    model_card_url: str | None = None
    is_active: bool | None = None
    context_window_size: int | None = None
    supports_ner: bool | None = None
    supports_vision: bool | None = None


__all__ = ["ModelRegistryCreate", "ModelRegistryRead", "ModelRegistryUpdate"]
