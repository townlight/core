"""
SQLAlchemy 2.x ORM model for the ``model_registry`` table.

Maps exactly to the Phase 1 baseline DDL:
  - id                  INTEGER PK (serial, DB-managed)
  - model_name          VARCHAR(255) NOT NULL
  - model_version       VARCHAR(100) nullable
  - parameter_count     VARCHAR(50)  nullable
  - license             VARCHAR(100) nullable
  - model_card_url      TEXT         nullable
  - is_active           BOOLEAN      NOT NULL DEFAULT false
  - added_at            TIMESTAMPTZ  nullable DEFAULT now()
  - context_window_size INTEGER      nullable
  - supports_ner        BOOLEAN      NOT NULL DEFAULT false
  - supports_vision     BOOLEAN      NOT NULL DEFAULT false
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from townlight_core.db import Base


class ModelRegistry(Base):
    """ORM model for the model_registry table."""

    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parameter_count: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_card_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    added_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    context_window_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supports_ner: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    supports_vision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ModelRegistry id={self.id!r} model_name={self.model_name!r} "
            f"is_active={self.is_active!r}>"
        )


__all__ = ["ModelRegistry"]
