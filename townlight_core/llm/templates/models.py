"""
SQLAlchemy 2.x ORM model for the ``prompt_templates`` table.

Maps exactly to the Phase 2 schema:
  - id                    UUID PK (Python-side default uuid4)
  - template_name         VARCHAR(200) NOT NULL
  - consumer_app          VARCHAR(100) NOT NULL DEFAULT 'townlight_core'
  - is_override           BOOLEAN      NOT NULL DEFAULT false
  - purpose               VARCHAR(50)  NOT NULL
  - system_prompt         TEXT         NOT NULL
  - user_prompt_template  TEXT         NOT NULL  (string.Template syntax)
  - token_budget          JSONB        nullable  DEFAULT {}
  - model_id              INTEGER FK → model_registry(id) ON DELETE SET NULL
  - version               INTEGER      NOT NULL  DEFAULT 1
  - is_active             BOOLEAN      NOT NULL  DEFAULT true
  - created_by            UUID FK → users(id) ON DELETE SET NULL
  - created_at            TIMESTAMPTZ  NOT NULL  DEFAULT now()

Unique constraint: UNIQUE(consumer_app, template_name, version)
  named uq_prompt_templates_app_name_version
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from townlight_core.db import Base


class PromptTemplate(Base):
    """ORM model for the prompt_templates table."""

    __tablename__ = "prompt_templates"

    __table_args__ = (
        UniqueConstraint(
            "consumer_app",
            "template_name",
            "version",
            name="uq_prompt_templates_app_name_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    template_name: Mapped[str] = mapped_column(String(200), nullable=False)
    consumer_app: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="townlight_core"
    )
    is_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    token_budget: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("model_registry.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    # NOTE: DB-level FK to users(id) ON DELETE SET NULL is created by the
    # 0001 baseline migration. The ORM-level ForeignKey reference is omitted
    # because townlight_core has no User ORM model — users.id lives in records-ai
    # and is not part of townlight_core.db.Base.metadata. Including the ORM-level
    # ForeignKey here causes NoReferencedTableError at mapper config time.
    # The DB constraint is unaffected.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PromptTemplate id={self.id!r} template_name={self.template_name!r} "
            f"consumer_app={self.consumer_app!r} version={self.version!r} "
            f"is_active={self.is_active!r}>"
        )


__all__ = ["PromptTemplate"]
