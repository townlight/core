"""
townlight_core.llm.registry — ORM model, Pydantic schemas, service, and router.

Public exports:

- ``ModelRegistry``        — SQLAlchemy ORM model (maps to the model_registry table).
- ``ModelRegistryCreate``  — Pydantic schema for POST (create).
- ``ModelRegistryRead``    — Pydantic schema for GET responses (ORM-compatible).
- ``ModelRegistryUpdate``  — Pydantic schema for PATCH (partial update).
- ``model_registry_router``         — FastAPI APIRouter for admin CRUD.
- ``get_active_model``              — Async service: fetch active model row or None.
- ``require_active_model``          — Async service: fetch or raise MissingModelError.
- ``get_active_model_context_window`` — Async service: active context_window_size or default.
- ``ModelRegistryServiceError``     — Service exception base.
- ``MissingModelError``             — Raised when a required active model is absent.
"""

from townlight_core.llm.registry.models import ModelRegistry
from townlight_core.llm.registry.router import router as model_registry_router
from townlight_core.llm.registry.schemas import (
    ModelRegistryCreate,
    ModelRegistryRead,
    ModelRegistryUpdate,
)
from townlight_core.llm.registry.service import (
    MissingModelError,
    ModelRegistryServiceError,
    get_active_model,
    get_active_model_context_window,
    require_active_model,
)

__all__ = [
    "ModelRegistry",
    "ModelRegistryCreate",
    "ModelRegistryRead",
    "ModelRegistryUpdate",
    "model_registry_router",
    "MissingModelError",
    "ModelRegistryServiceError",
    "get_active_model",
    "require_active_model",
    "get_active_model_context_window",
]
