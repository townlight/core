"""FastAPI APIRouter for ModelRegistry admin CRUD.

Mount this router on a consumer FastAPI app, overriding ``get_session`` with
the consumer's own AsyncSession dependency. Without an override, every
endpoint raises a clear 500 directing the operator to wire the dependency.

Records-ai will mount this in its admin app and override ``get_session`` with
its existing async session dependency.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from townlight_core.llm.registry.models import ModelRegistry
from townlight_core.llm.registry.schemas import (
    ModelRegistryCreate,
    ModelRegistryRead,
    ModelRegistryUpdate,
)


def _unconfigured_session_dependency() -> AsyncSession:
    """Placeholder dependency.

    Consumers must override via FastAPI's
    ``app.dependency_overrides[get_session] = my_session_provider``.
    """
    raise RuntimeError(
        "townlight_core.llm.registry.router.get_session has not been overridden. "
        "Mount the router on your FastAPI app with a session dependency: "
        "`app.dependency_overrides[get_session] = your_session_provider`."
    )


def get_session() -> AsyncSession:  # pragma: no cover - overridden in production
    """Default session dependency. Always raises until overridden."""
    return _unconfigured_session_dependency()


router = APIRouter(prefix="/admin/models", tags=["model_registry"])


@router.get("", response_model=list[ModelRegistryRead])
async def list_models(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ModelRegistry).order_by(ModelRegistry.id))
    rows = result.scalars().all()
    return rows


@router.get("/{model_id}", response_model=ModelRegistryRead)
async def get_model(model_id: int, session: AsyncSession = Depends(get_session)):
    row = await session.get(ModelRegistry, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return row


@router.post("", response_model=ModelRegistryRead, status_code=201)
async def create_model(
    payload: ModelRegistryCreate,
    session: AsyncSession = Depends(get_session),
):
    row = ModelRegistry(**payload.model_dump(exclude_unset=True))
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.patch("/{model_id}", response_model=ModelRegistryRead)
async def update_model(
    model_id: int,
    payload: ModelRegistryUpdate,
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(ModelRegistry, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return row


@router.delete("/{model_id}", status_code=204)
async def delete_model(
    model_id: int,
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(ModelRegistry, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    await session.delete(row)
    await session.commit()


__all__ = ["router", "get_session"]
