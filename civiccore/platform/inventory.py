# SPDX-License-Identifier: AGPL-3.0-only
"""Persisted, scoped installed-module inventory and deterministic recommendations.

Scope and non-claims
--------------------
This module records *what a named scope declares it has installed and enabled* and derives
recommendations from those declarations. It never scans a machine, calls a server, enumerates
packages, downloads, installs, enables or disables anything. A recommendation is advice about
declared metadata; it is not installation evidence and it is not a health claim.

Relationship to the existing contracts
--------------------------------------
There is exactly one module resolver: :func:`civiccore.platform.modules.build_module_registry`.
This module validates through the shipped :class:`~civiccore.platform.modules.ModuleManifest`,
persists a declared inventory, and asks that resolver what the declared set actually admits.
No second resolver, dependency walker or cycle detector exists here.

Relationship to the shared municipal systems catalog
----------------------------------------------------
``civiccore.catalog`` holds reference data about *vendor systems* (domains, vendors, protocol
templates). That is not this: an installed-module inventory lists *Townlight module packages* a
scope declares installed. The two never share rows, and a catalog entry never implies a module
installation, just as a module entry never implies a vendor connection.

Scope and persistence
---------------------
One inventory row set is keyed by ``(scope_id, revision)``. ``scope_id`` is a caller-supplied
deployment scope (for example a city profile identifier); Core does not invent, enumerate or
authenticate one. Revisions are append-only: a write either appends the next revision or is
refused. ``expected_revision`` is a compare-and-append guard so a stale writer cannot overwrite
another writer's newer declaration. The application still owns authentication, authorization
and the transaction (commit/rollback).

Determinism
-----------
Recommendations are a pure function of (declared inventory, caller-supplied available
manifests, installed Core version). Ordering is by ``(module_id, action)`` and reasons come from
the shared resolver, so identical inputs produce byte-identical output. "Available" manifests
are passed in explicitly by the caller; nothing is discovered.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from civiccore.platform.modules import (
    InstallProfile,
    ModuleManifest,
    ModuleRegistryState,
    build_module_registry,
)

__all__ = [
    "ModuleInventoryError",
    "UnknownModuleError",
    "StaleInventoryError",
    "InventoryConflictError",
    "ModuleInventoryEntry",
    "ModuleInventory",
    "ModuleRecommendation",
    "InventoryOutcome",
    "record_inventory",
    "current_inventory",
    "inventory_revision",
    "inventory_history",
    "require_installed",
    "module_recommendations",
    "HEAD_TABLE",
    "ENTRY_TABLE",
]

HEAD_TABLE = "civiccore_module_inventory"
ENTRY_TABLE = "civiccore_module_inventory_entries"

SCOPE_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")

RecommendationAction = Literal[
    "install", "enable", "resolve-dependency", "upgrade-core", "not-supported"
]
RecommendationBasis = Literal["installed", "available"]


class ModuleInventoryError(ValueError):
    """Base class: the inventory write or read was refused and nothing changed."""


class UnknownModuleError(ModuleInventoryError):
    """A referenced module id is not part of the scope's declared inventory."""


class StaleInventoryError(ModuleInventoryError):
    """The declared revision moved on; re-read before writing."""


class InventoryConflictError(ModuleInventoryError):
    """That revision already exists with different content."""


def _require_scope(scope_id: str) -> str:
    if not isinstance(scope_id, str) or not SCOPE_PATTERN.fullmatch(scope_id):
        raise ModuleInventoryError(
            "scope_id must be a lowercase identifier of 2-64 characters "
            "(letters, digits, dot, dash, underscore)"
        )
    return scope_id


def _as_json(value: Any) -> Any:
    """asyncpg may hand jsonb back as text; normalise without guessing at content."""
    return json.loads(value) if isinstance(value, str) else value


class ModuleInventoryEntry(BaseModel):
    """One module the scope declares it has, plus the manifest it was installed from."""

    model_config = ConfigDict(extra="forbid")

    module_id: str = Field(min_length=2, max_length=64)
    version: str = Field(min_length=1)
    enabled: bool
    manifest: ModuleManifest

    @model_validator(mode="after")
    def bind_manifest(self) -> ModuleInventoryEntry:
        if self.manifest.module_id != self.module_id:
            raise ValueError("entry module_id does not match its manifest")
        if self.manifest.version != self.version:
            raise ValueError("entry version does not match its manifest")
        return self


class ModuleInventory(BaseModel):
    """A scope's declared installed/enabled module set at one revision."""

    model_config = ConfigDict(extra="forbid")

    scope_id: str = Field(min_length=2, max_length=64)
    revision: int = Field(ge=1)
    profile: InstallProfile = "windows_local"
    civiccore_version: str = Field(min_length=1)
    entries: list[ModuleInventoryEntry] = Field(default_factory=list)

    @field_validator("scope_id")
    @classmethod
    def validate_scope(cls, value: str) -> str:
        return _require_scope(value)

    @model_validator(mode="after")
    def validate_entries(self) -> ModuleInventory:
        ids = [entry.module_id for entry in self.entries]
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            raise ValueError(f"duplicate module ids: {', '.join(duplicates)}")
        return self

    @property
    def installed_module_ids(self) -> list[str]:
        return sorted(entry.module_id for entry in self.entries)

    @property
    def enabled_module_ids(self) -> list[str]:
        return sorted(entry.module_id for entry in self.entries if entry.enabled)

    def fingerprint(self) -> str:
        """Stable content hash over the declared set, independent of caller ordering."""
        payload = [
            {
                "module_id": entry.module_id,
                "version": entry.version,
                "enabled": entry.enabled,
                "manifest": entry.manifest.model_dump(mode="json"),
            }
            for entry in sorted(self.entries, key=lambda item: item.module_id)
        ]
        blob = json.dumps(
            {
                "scope_id": self.scope_id,
                "profile": self.profile,
                "civiccore_version": self.civiccore_version,
                "entries": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def require_installed(inventory: ModuleInventory, module_ids: list[str]) -> None:
    """Refuse module ids the scope has not declared installed."""
    unknown = sorted(set(module_ids) - set(inventory.installed_module_ids))
    if unknown:
        raise UnknownModuleError(
            f"modules are not installed in scope {inventory.scope_id!r}: {', '.join(unknown)}"
        )


class InventoryOutcome(BaseModel):
    """Result of one append attempt."""

    model_config = ConfigDict(extra="forbid")

    inventory: ModuleInventory
    inserted: bool
    fingerprint: str


_COLUMNS = "scope_id,revision,profile,civiccore_version,content_sha256"


def _entry_rows(entries: list[ModuleInventoryEntry]) -> list[dict[str, Any]]:
    return [
        {
            "module": entry.module_id,
            "version": entry.version,
            "enabled": entry.enabled,
            "manifest": json.dumps(entry.manifest.model_dump(mode="json"), sort_keys=True),
        }
        for entry in sorted(entries, key=lambda item: item.module_id)
    ]


async def _load(
    session: AsyncSession, scope_id: str, revision: int | None
) -> ModuleInventory | None:
    if revision is None:
        header = (
            (
                await session.execute(
                    text(
                        f"SELECT {_COLUMNS} FROM {HEAD_TABLE} WHERE scope_id=:scope "
                        "ORDER BY revision DESC LIMIT 1"
                    ),
                    {"scope": scope_id},
                )
            )
            .mappings()
            .first()
        )
    else:
        header = (
            (
                await session.execute(
                    text(
                        f"SELECT {_COLUMNS} FROM {HEAD_TABLE} "
                        "WHERE scope_id=:scope AND revision=:rev"
                    ),
                    {"scope": scope_id, "rev": revision},
                )
            )
            .mappings()
            .first()
        )
    if header is None:
        return None
    rows = (
        (
            await session.execute(
                text(
                    f"SELECT module_id,version,enabled,manifest FROM {ENTRY_TABLE} "
                    "WHERE scope_id=:scope AND revision=:rev ORDER BY module_id"
                ),
                {"scope": scope_id, "rev": header["revision"]},
            )
        )
        .mappings()
        .all()
    )
    return ModuleInventory(
        scope_id=header["scope_id"],
        revision=header["revision"],
        profile=header["profile"],
        civiccore_version=header["civiccore_version"],
        entries=[
            ModuleInventoryEntry(
                module_id=row["module_id"],
                version=row["version"],
                enabled=row["enabled"],
                manifest=ModuleManifest.model_validate(_as_json(row["manifest"])),
            )
            for row in rows
        ],
    )


async def record_inventory(
    session: AsyncSession,
    inventory: dict | ModuleInventory,
    *,
    recorded_by: str,
    expected_revision: int | None = None,
) -> InventoryOutcome:
    """Append one declared inventory revision, or verify an exact repeat of one.

    ``expected_revision`` is a compare-and-append guard: ``None`` skips it, ``0`` means "this
    scope has no inventory yet", any other value must equal the stored maximum revision. A
    stale guard, an out-of-sequence revision or changed content for an existing revision raises
    rather than overwriting. The caller commits.
    """
    if not isinstance(recorded_by, str) or not recorded_by.strip() or len(recorded_by) > 128:
        raise ModuleInventoryError("An attributed recorder identity is required")
    item = (
        inventory
        if isinstance(inventory, ModuleInventory)
        else ModuleInventory.model_validate(inventory)
    )
    fingerprint = item.fingerprint()

    # Serialize per scope so two writers cannot both believe they hold the next revision.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"civiccore.module_inventory:{item.scope_id}"},
    )

    current = (
        (
            await session.execute(
                text(
                    f"SELECT revision,content_sha256 FROM {HEAD_TABLE} WHERE scope_id=:scope "
                    "ORDER BY revision DESC LIMIT 1"
                ),
                {"scope": item.scope_id},
            )
        )
        .mappings()
        .first()
    )
    current_revision = current["revision"] if current else 0

    if expected_revision is not None:
        if expected_revision < 0:
            raise ModuleInventoryError("expected_revision cannot be negative")
        if expected_revision != current_revision:
            raise StaleInventoryError(
                "Inventory moved on; re-read the current revision before appending"
            )

    if current and item.revision == current_revision:
        if current["content_sha256"] != fingerprint:
            raise InventoryConflictError(
                "That revision already exists with a different declared inventory"
            )
        loaded = await _load(session, item.scope_id, current_revision)
        assert loaded is not None
        return InventoryOutcome(inventory=loaded, inserted=False, fingerprint=fingerprint)

    if item.revision <= current_revision:
        raise StaleInventoryError(
            "Revisions are append-only and are never backfilled or renumbered"
        )
    if item.revision != current_revision + 1:
        raise StaleInventoryError("Submitted revision is not the next revision number")

    await session.execute(
        text(
            f"INSERT INTO {HEAD_TABLE} (scope_id,revision,profile,civiccore_version,"
            "content_sha256,recorded_by) VALUES (:scope,:rev,:profile,:core,:digest,:actor)"
        ),
        {
            "scope": item.scope_id,
            "rev": item.revision,
            "profile": item.profile,
            "core": item.civiccore_version,
            "digest": fingerprint,
            "actor": recorded_by.strip(),
        },
    )
    for row in _entry_rows(item.entries):
        await session.execute(
            text(
                f"INSERT INTO {ENTRY_TABLE} (scope_id,revision,module_id,version,enabled,manifest) "
                "VALUES (:scope,:rev,:module,:version,:enabled,CAST(:manifest AS jsonb))"
            ),
            {"scope": item.scope_id, "rev": item.revision, **row},
        )
    loaded = await _load(session, item.scope_id, item.revision)
    assert loaded is not None
    return InventoryOutcome(inventory=loaded, inserted=True, fingerprint=fingerprint)


async def current_inventory(session: AsyncSession, scope_id: str) -> ModuleInventory | None:
    """Latest declared inventory for exactly one scope, or ``None`` if it has none."""
    return await _load(session, _require_scope(scope_id), None)


async def inventory_revision(
    session: AsyncSession, scope_id: str, revision: int
) -> ModuleInventory | None:
    """One exact revision, scoped; another scope's revision is never returned."""
    if revision < 1:
        raise ModuleInventoryError("revision must be >= 1")
    return await _load(session, _require_scope(scope_id), revision)


async def inventory_history(session: AsyncSession, scope_id: str) -> list[int]:
    """Recorded revision numbers for one scope, oldest first."""
    rows = await session.execute(
        text(f"SELECT revision FROM {HEAD_TABLE} WHERE scope_id=:scope ORDER BY revision"),
        {"scope": _require_scope(scope_id)},
    )
    return [row[0] for row in rows]


class ModuleRecommendation(BaseModel):
    """Advisory next step for one module. Never installation or health evidence."""

    model_config = ConfigDict(extra="forbid")

    module_id: str = Field(min_length=2, max_length=64)
    action: RecommendationAction
    basis: RecommendationBasis
    reasons: list[str] = Field(min_length=1)
    operator_action: str = Field(min_length=1)


def _actions_for_reason(reason: str | None) -> RecommendationAction:
    if reason is None:
        return "enable"
    if reason.startswith("Requires Core"):
        return "upgrade-core"
    if "is not available for the" in reason:
        return "not-supported"
    return "resolve-dependency"


def _registry(
    manifests: list[ModuleManifest],
    *,
    civiccore_version: str,
    selected: set[str],
    profile: InstallProfile,
) -> ModuleRegistryState:
    return build_module_registry(
        list(manifests),
        civiccore_version=civiccore_version,
        selected_module_ids=selected,
        profile=profile,
    )


def module_recommendations(
    inventory: ModuleInventory,
    available_manifests: list[ModuleManifest | dict[str, Any]] | None = None,
) -> list[ModuleRecommendation]:
    """Deterministic advisory recommendations for one declared inventory.

    ``available_manifests`` are module packages the caller states are present for this scope
    (for example unpacked beside the deployment). They are never discovered, downloaded or
    installed here, and an absent argument means no availability is claimed. Every answer comes
    from the shipped resolver over the declarations supplied, so an admitted module is reported
    as admitted on those declarations and nothing more.
    """
    installed_manifests = [entry.manifest for entry in inventory.entries]
    available = [
        item if isinstance(item, ModuleManifest) else ModuleManifest.model_validate(item)
        for item in (available_manifests or [])
    ]
    installed_ids = set(inventory.installed_module_ids)
    # The resolver sees exactly the manifests handed in: the scope's declared installs plus
    # whatever the caller stated is available. Nothing is read from disk or the network.
    known: dict[str, ModuleManifest] = {item.module_id: item for item in installed_manifests}
    for item in available:
        known[item.module_id] = item
    manifests = list(known.values())
    enabled = set(inventory.enabled_module_ids)
    enabled_installed = enabled & installed_ids

    def resolve(selected: set[str]) -> dict[str, object]:
        return {
            entry.module_id: entry
            for entry in _registry(
                manifests,
                civiccore_version=inventory.civiccore_version,
                selected=selected,
                profile=inventory.profile,
            ).entries
        }

    actual = resolve(enabled_installed)
    if_disabled_were_on = resolve(enabled_installed | (installed_ids - enabled))

    found: list[ModuleRecommendation] = []
    for entry in sorted(inventory.entries, key=lambda item: item.module_id):
        resolved = actual[entry.module_id]
        if not entry.enabled:
            candidate = if_disabled_were_on[entry.module_id]
            action = "enable" if candidate.enabled else _actions_for_reason(candidate.reason)
            reasons = [
                candidate.reason
                or "Every required dependency of this installed module is declared and compatible."
            ]
            found.append(
                ModuleRecommendation(
                    module_id=entry.module_id,
                    action=action,
                    basis="installed",
                    reasons=reasons,
                    operator_action=_operator_copy(entry.manifest.name, action, reasons[0]),
                )
            )
        elif resolved.status != "enabled":
            reasons = [resolved.reason or "The declared module set does not admit this module."]
            action = _actions_for_reason(resolved.reason)
            found.append(
                ModuleRecommendation(
                    module_id=entry.module_id,
                    action=action,
                    basis="installed",
                    reasons=reasons,
                    operator_action=_operator_copy(entry.manifest.name, action, reasons[0]),
                )
            )

    for entry in sorted(available, key=lambda item: item.module_id):
        if entry.module_id in installed_ids:
            continue
        trial = resolve(enabled_installed | {entry.module_id})[entry.module_id]
        action = "install" if trial.enabled else _actions_for_reason(trial.reason)
        reasons = [
            trial.reason
            or "Every required dependency of this package is declared installed and compatible."
        ]
        found.append(
            ModuleRecommendation(
                module_id=entry.module_id,
                action=action,
                basis="available",
                reasons=reasons,
                operator_action=_operator_copy(entry.name, action, reasons[0]),
            )
        )

    return sorted(found, key=lambda item: (item.module_id, item.action))


def _operator_copy(name: str, action: RecommendationAction, reason: str) -> str:
    if action == "install":
        return (
            f"Nothing is installed yet. Review whether {name} belongs in this deployment: "
            f"{reason}"
        )
    if action == "enable":
        return f"{name} is installed but switched off. Enabling it is optional: {reason}"
    if action == "upgrade-core":
        return f"{name} needs a newer CivicCore before it can run: {reason}"
    if action == "not-supported":
        return f"{name} does not support this install profile: {reason}"
    return f"{name} cannot start with the modules declared here: {reason}"
