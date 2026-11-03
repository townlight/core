"""In-process task handler registry for local Townlight workers."""

from __future__ import annotations

from collections.abc import Callable

from townlight_core.platform.task_queue import TaskHandler

_HANDLERS: dict[str, TaskHandler] = {}


def register_task_handler(task_type: str) -> Callable[[TaskHandler], TaskHandler]:
    """Register a callable task handler by task type."""

    if not task_type.strip():
        raise ValueError("task_type cannot be blank")

    def decorator(handler: TaskHandler) -> TaskHandler:
        _HANDLERS[task_type] = handler
        return handler

    return decorator


def get_task_handlers() -> dict[str, TaskHandler]:
    """Return a copy of the registered task handlers."""

    return dict(_HANDLERS)
