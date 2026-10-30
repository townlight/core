# SPDX-License-Identifier: AGPL-3.0-only
"""Validated input contract for generating one Townlight module project.

The generator's leverage is real: every accepted name becomes a package name,
an import path, an environment-variable prefix and a filesystem path. Names are
therefore admitted by allow-list, never by sanitising. A name that is not a
plain lower-case module id is refused with ``InvalidModuleSpecError`` instead of
being rewritten into something the caller did not ask for.
"""

from __future__ import annotations

import keyword
import re
import sys
from dataclasses import dataclass

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from civiccore.platform.modules import MODULE_ID_PATTERN, SLUG_PATTERN

ROUTE_PATH_PATTERN = r"^/[a-z0-9/_:-]*$"

#: Ids that would collide with Core, with the generated layout's own directory
#: names, or with the reserved module ids Core already ships around.
RESERVED_MODULE_IDS = frozenset(
    {
        "civiccore",
        "civicsuite",
        "tests",
        "test",
        "docs",
        "app",
        "config",
        "migrations",
        "settings",
        "scaffold",
        "platform",
        "modules",
    }
)


class ScaffoldError(Exception):
    """Base class for refused scaffold operations."""


class InvalidModuleSpecError(ScaffoldError, ValueError):
    """A requested module name or option is not admissible."""


class UnsafeTargetError(ScaffoldError):
    """The requested output location is refused before anything is written."""


class TargetExistsError(ScaffoldError):
    """The requested output location already exists; nothing is overwritten."""


class PathContainmentError(ScaffoldError):
    """A planned file path would escape the generated project root."""


class ModuleSpec(BaseModel):
    """Everything the generator needs, already validated.

    ``module_id`` is the only identity; ``package_name``, import path, env-var
    prefix and migration revision ids are derived from it so a caller cannot
    create an inconsistent project.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    module_id: str = Field(pattern=MODULE_ID_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=12, max_length=500)
    version: str = "0.1.0"
    civiccore_min_version: str = "1.3.0.dev1"
    permission_key: str | None = Field(default=None, pattern=SLUG_PATTERN)
    staff_roles: tuple[str, ...] = ("staff",)
    route_path: str | None = Field(default=None, pattern=ROUTE_PATH_PATTERN)

    @field_validator("name", "description")
    @classmethod
    def validate_text_is_single_line(cls, value: str) -> str:
        if value != " ".join(value.split()):
            raise ValueError("value must be single-line text without runs of whitespace")
        return value

    @field_validator("staff_roles")
    @classmethod
    def validate_staff_roles(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("staff_roles must name at least one role")
        for role in value:
            if not re.fullmatch(SLUG_PATTERN, role):
                raise ValueError(f"role {role!r} is not a lower-case role id")
        return value

    @model_validator(mode="after")
    def validate_derived_identity(self) -> ModuleSpec:
        assert_admissible_module_id(self.module_id)
        for label, raw in (
            ("version", self.version),
            ("civiccore_min_version", self.civiccore_min_version),
        ):
            try:
                Version(raw)
            except InvalidVersion as exc:  # pragma: no cover - defensive
                raise ValueError(f"{label} must be a PEP 440 version: {exc}") from exc
        return self

    @property
    def package_name(self) -> str:
        return self.module_id.replace("-", "_")

    @property
    def env_prefix(self) -> str:
        return self.package_name.upper()

    @property
    def token_roles_env_var(self) -> str:
        return f"{self.env_prefix}_TOKEN_ROLES"

    @property
    def permission(self) -> str:
        return self.permission_key or f"{self.module_id}-use"

    @property
    def route(self) -> str:
        return self.route_path or f"/{self.module_id}"

    @property
    def baseline_revision(self) -> str:
        return f"{self.package_name}_0001_baseline"


def assert_admissible_module_id(module_id: str) -> str:
    """Refuse ids that would produce a colliding or unsafe project.

    Rejection, not sanitisation: a caller that asks for ``../evil`` or ``App``
    gets an error naming the rule, never a quietly rewritten directory.
    """

    if not re.fullmatch(MODULE_ID_PATTERN, module_id):
        raise InvalidModuleSpecError(
            "module_id must match ^[a-z][a-z0-9-]{1,63}$ (lower-case letters, digits "
            f"and hyphens, starting with a letter); got {module_id!r}"
        )
    package_name = module_id.replace("-", "_")
    if module_id in RESERVED_MODULE_IDS or package_name in RESERVED_MODULE_IDS:
        raise InvalidModuleSpecError(f"module_id {module_id!r} is reserved by CivicCore")
    if keyword.iskeyword(package_name):
        raise InvalidModuleSpecError(f"module_id {module_id!r} derives a Python keyword")
    if package_name in sys.stdlib_module_names:
        raise InvalidModuleSpecError(
            f"module_id {module_id!r} derives package name {package_name!r}, "
            "which is a Python standard-library module"
        )
    return module_id


@dataclass(frozen=True)
class ScaffoldOptions:
    """Non-identity options, kept out of the persisted manifest."""

    dry_run: bool = False
