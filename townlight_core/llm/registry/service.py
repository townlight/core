"""Service layer for the townlight_core LLM model registry.

Library-friendly: callers pass an AsyncSession explicitly (no hardcoded
session_maker). Used by downstream apps (records-ai, townlight_meetings) and by
internal townlight_core code that needs the active model's metadata.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from townlight_core.llm.context import DEFAULT_CONTEXT_WINDOW
from townlight_core.llm.registry.models import ModelRegistry

logger = logging.getLogger(__name__)


class ModelRegistryServiceError(Exception):
    """Base for ModelRegistry service errors."""


class MissingModelError(ModelRegistryServiceError):
    """Raised when caller required an active model and none exists."""


async def get_active_model(session: AsyncSession) -> ModelRegistry | None:
    """Return the active ModelRegistry row, or None if none active.

    By design, exactly one row should have is_active=True at runtime.
    If multiple are active, the lowest id wins (stable across reads); this
    is a minor invariant violation that should be surfaced via admin UI but
    does not crash the service.
    """
    stmt = (
        select(ModelRegistry)
        .where(ModelRegistry.is_active.is_(True))
        .order_by(ModelRegistry.id.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def require_active_model(session: AsyncSession) -> ModelRegistry:
    """Like get_active_model but raises MissingModelError if none exists."""
    row = await get_active_model(session)
    if row is None:
        raise MissingModelError(
            "No active model in model_registry. Insert a row with is_active=true "
            "(e.g. via the admin router or directly), or set the existing model "
            "to active."
        )
    return row


async def get_active_model_context_window(session: AsyncSession) -> int:
    """Return active model's context_window_size, or DEFAULT_CONTEXT_WINDOW.

    Default: 8192. Used by context-budget assembly when the registry is empty
    or the active row has no explicit context_window_size set (None or <=0).
    """
    row = await get_active_model(session)
    if row is None or row.context_window_size is None or row.context_window_size <= 0:
        logger.debug(
            "No active model or no context_window_size; defaulting to %d",
            DEFAULT_CONTEXT_WINDOW,
        )
        return DEFAULT_CONTEXT_WINDOW
    return row.context_window_size


__all__ = [
    "ModelRegistryServiceError",
    "MissingModelError",
    "get_active_model",
    "require_active_model",
    "get_active_model_context_window",
]
