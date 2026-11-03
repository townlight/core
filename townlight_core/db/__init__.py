"""
Shared SQLAlchemy declarative base for all townlight_core ORM models.

All ORM models in townlight_core (and downstream consumers such as townlight_records)
should inherit from this ``Base`` class so that metadata is shared across the
same declarative registry.  In Phase 2 Step 5, townlight_records will migrate its
own models to import and inherit from this Base rather than maintaining a
separate one.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all townlight_core ORM models."""


__all__ = ["Base"]
