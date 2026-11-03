"""In-process decorator registry for LLM providers.

Per ADR-0004 §6, townlight_core uses a simple in-process decorator registry rather
than setuptools entry-points to discover :class:`LLMProvider` implementations.
At one-process FastAPI scale (the records-ai deployment shape today), the
entry-points machinery adds packaging-time and import-time overhead with no
operational benefit: every provider that ships in this package can register
itself by being imported, and out-of-tree providers can register themselves
the same way from application code.

If a third-party plugin ecosystem materializes in v0.3.0 or later, an
entry-points discovery layer can be added on top of this registry without
breaking the in-process API — that is an additive change.

Behavioral notes:

* Registration is **strict**: re-registering an existing name raises
  :class:`ValueError`. ADR-0004 §6 explicitly forbids silent override because
  duplicate names are almost always a bug (two modules colliding) and a
  silent winner makes the bug essentially invisible.
* :func:`get_provider` constructs a fresh instance on every call, forwarding
  ``**config`` to the provider's ``__init__``. Caching is the caller's job
  — providers vary widely in whether they hold connection pools, API keys,
  or per-request state, and the registry should not assume.
"""

from __future__ import annotations

from typing import Callable

from townlight_core.llm.providers.base import LLMProvider

__all__ = [
    "PROVIDER_REGISTRY",
    "register_provider",
    "get_provider",
    "list_providers",
]


PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {}


def register_provider(
    name: str,
) -> Callable[[type[LLMProvider]], type[LLMProvider]]:
    """Decorator to register an :class:`LLMProvider` subclass under a stable name.

    Raises:
        TypeError: if the decorated class is not an :class:`LLMProvider`
            subclass.
        ValueError: if ``name`` is already taken (no silent override per
            ADR-0004 §6).
    """

    def decorator(cls: type[LLMProvider]) -> type[LLMProvider]:
        if not issubclass(cls, LLMProvider):
            raise TypeError(
                f"register_provider({name!r}) target must be an "
                f"LLMProvider subclass; got {cls!r}"
            )
        if name in PROVIDER_REGISTRY:
            raise ValueError(
                f"Provider {name!r} already registered "
                f"(existing: {PROVIDER_REGISTRY[name]!r})"
            )
        PROVIDER_REGISTRY[name] = cls
        return cls

    return decorator


def get_provider(name: str, **config) -> LLMProvider:
    """Construct a provider by name, forwarding ``**config`` to its ``__init__``.

    Raises:
        KeyError: if ``name`` is not registered.
    """
    if name not in PROVIDER_REGISTRY:
        raise KeyError(
            f"Provider {name!r} not registered. "
            f"Available: {sorted(PROVIDER_REGISTRY)}"
        )
    return PROVIDER_REGISTRY[name](**config)


def list_providers() -> list[str]:
    """Return a sorted list of registered provider names."""
    return sorted(PROVIDER_REGISTRY.keys())
