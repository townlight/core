"""Module manifest and registry contracts for local Townlight deployments."""

from __future__ import annotations

from typing import Any, Literal

from packaging.version import Version
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ModuleSurface = Literal["staff", "resident", "admin", "system"]
InstallProfile = Literal["windows_local", "server", "developer"]
ServiceType = Literal[
    "python-service",
    "postgres-schema",
    "file-store",
    "ollama-model",
    "tauri-command",
    "local-api",
    "background-worker",
]
RuntimeRequirementKind = Literal[
    "civiccore",
    "postgres",
    "pgvector",
    "python",
    "file_storage",
    "ollama",
    "llm_model",
    "tauri_command",
    "local_api",
    "windows_service",
    "webview2",
    "external_connector",
    "docker",
    "wsl",
    "linux_shell",
    "terminal",
]
ModuleRegistryStatus = Literal["enabled", "disabled", "blocked"]

MODULE_ID_PATTERN = r"^[a-z][a-z0-9-]{1,63}$"
SLUG_PATTERN = r"^[a-z][a-z0-9_-]{1,63}$"
WINDOWS_LOCAL_BLOCKED_RUNTIME_KINDS = frozenset({"docker", "wsl", "linux_shell", "terminal"})


class ModuleDependency(BaseModel):
    """Another Townlight module required by a manifest."""

    model_config = ConfigDict(extra="forbid")

    module_id: str = Field(pattern=MODULE_ID_PATTERN)
    min_version: str | None = Field(default=None, min_length=1)
    required: bool = True


class ModulePermission(BaseModel):
    """Permission surfaced to the shell and module manager."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=SLUG_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    surface: ModuleSurface = "staff"
    roles: list[str] = Field(default_factory=list)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("roles must name at least one role that grants the permission")
        return value


class ModuleRoute(BaseModel):
    """A route the desktop shell may expose for a module."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=SLUG_PATTERN)
    path: str = Field(pattern=r"^/[a-z0-9/_:-]*$")
    label: str = Field(min_length=1)
    surface: ModuleSurface = "staff"
    permission: str | None = Field(default=None, pattern=SLUG_PATTERN)


class ModuleService(BaseModel):
    """A local service, schema, or command needed by a module."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=SLUG_PATTERN)
    service_type: ServiceType
    description: str = Field(min_length=1)
    required: bool = True
    start_order: int = Field(default=100, ge=0)
    health_check_id: str | None = Field(default=None, pattern=SLUG_PATTERN)


class ModuleMigration(BaseModel):
    """A migration contract that the installer/runtime must apply or verify."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=SLUG_PATTERN)
    description: str = Field(min_length=1)
    owner_schema: str | None = Field(default=None, min_length=1)
    required: bool = True


class ModuleHealthCheck(BaseModel):
    """A module health check known to the umbrella health center."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=SLUG_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    blocking: bool = True
    surface: Literal["staff", "admin", "system"] = "admin"
    repair_action: str | None = Field(default=None, min_length=1)


class ModuleBackupHook(BaseModel):
    """A backup/restore hook the module contributes to the shared backup plan."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=SLUG_PATTERN)
    label: str = Field(min_length=1)
    includes: list[str] = Field(min_length=1)
    restore_supported: bool = True


class ModuleModelRequirement(BaseModel):
    """A model requirement declared by a module."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=SLUG_PATTERN)
    provider: Literal["ollama", "local", "none", "openai", "anthropic"] = "ollama"
    model_name: str = Field(min_length=1)
    required: bool = True
    local_only: bool = True
    minimum_context_tokens: int | None = Field(default=None, ge=1)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    download_url: str | None = Field(default=None, min_length=1)
    license_name: str | None = Field(default=None, min_length=1)


class ModuleRuntimeRequirement(BaseModel):
    """Runtime capability needed by a module."""

    model_config = ConfigDict(extra="forbid")

    kind: RuntimeRequirementKind
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool = True
    operator_visible: bool = False


class ModuleManifest(BaseModel):
    """Complete manifest for a Townlight module package."""

    model_config = ConfigDict(extra="forbid")

    module_id: str = Field(pattern=MODULE_ID_PATTERN)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    package_name: str = Field(min_length=1)
    civiccore_min_version: str = Field(min_length=1)
    enabled_by_default: bool = True
    surfaces: list[ModuleSurface] = Field(default_factory=lambda: ["staff"])
    install_profiles: list[InstallProfile] = Field(default_factory=lambda: ["windows_local"])
    dependencies: list[ModuleDependency] = Field(default_factory=list)
    routes: list[ModuleRoute] = Field(default_factory=list)
    permissions: list[ModulePermission] = Field(default_factory=list)
    services: list[ModuleService] = Field(default_factory=list)
    migrations: list[ModuleMigration] = Field(default_factory=list)
    health_checks: list[ModuleHealthCheck] = Field(default_factory=list)
    backup_hooks: list[ModuleBackupHook] = Field(default_factory=list)
    model_requirements: list[ModuleModelRequirement] = Field(default_factory=list)
    runtime_requirements: list[ModuleRuntimeRequirement] = Field(default_factory=list)
    settings_schema_version: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("surfaces", "install_profiles")
    @classmethod
    def validate_non_empty_list(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("list must contain at least one item")
        return value

    @model_validator(mode="after")
    def validate_cross_references(self) -> ModuleManifest:
        _assert_unique("permission", [item.key for item in self.permissions])
        _assert_unique("route", [item.id for item in self.routes])
        _assert_unique("service", [item.id for item in self.services])
        _assert_unique("migration", [item.id for item in self.migrations])
        _assert_unique("health_check", [item.id for item in self.health_checks])
        _assert_unique("backup_hook", [item.id for item in self.backup_hooks])
        _assert_unique("model_requirement", [item.id for item in self.model_requirements])

        permission_keys = {item.key for item in self.permissions}
        for route in self.routes:
            if route.permission and route.permission not in permission_keys:
                raise ValueError(
                    f"route {route.id!r} references unknown permission {route.permission!r}"
                )

        health_check_ids = {item.id for item in self.health_checks}
        for service in self.services:
            if service.health_check_id and service.health_check_id not in health_check_ids:
                raise ValueError(
                    f"service {service.id!r} references unknown health check "
                    f"{service.health_check_id!r}"
                )

        for dependency in self.dependencies:
            if dependency.module_id == self.module_id:
                raise ValueError("module cannot depend on itself")

        if "windows_local" in self.install_profiles:
            _validate_windows_runtime_requirements(self)

        return self


class ModuleRegistryEntry(BaseModel):
    """One module's resolved state in a runtime profile."""

    model_config = ConfigDict(extra="forbid")

    module_id: str = Field(pattern=MODULE_ID_PATTERN)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    enabled: bool
    locked: bool = False
    status: ModuleRegistryStatus
    reason: str | None = None
    manifest: ModuleManifest


class ModuleRegistryState(BaseModel):
    """Resolved module registry for the desktop shell and installer."""

    model_config = ConfigDict(extra="forbid")

    profile: InstallProfile = "windows_local"
    civiccore_version: str = Field(min_length=1)
    civiccore_locked: bool = True
    entries: list[ModuleRegistryEntry]

    @property
    def enabled_module_ids(self) -> list[str]:
        return [entry.module_id for entry in self.entries if entry.enabled]

    @property
    def blocked_module_ids(self) -> list[str]:
        return [entry.module_id for entry in self.entries if entry.status == "blocked"]


def validate_windows_local_manifest(manifest: ModuleManifest | dict[str, Any]) -> ModuleManifest:
    """Validate a manifest for the Windows desktop profile."""

    parsed = (
        manifest
        if isinstance(manifest, ModuleManifest)
        else ModuleManifest.model_validate(manifest)
    )
    if "windows_local" not in parsed.install_profiles:
        raise ValueError(f"{parsed.module_id} does not declare support for windows_local")
    _validate_windows_runtime_requirements(parsed)
    return parsed


def build_module_registry(
    manifests: list[ModuleManifest | dict[str, Any]],
    *,
    civiccore_version: str,
    selected_module_ids: set[str] | None = None,
    profile: InstallProfile = "windows_local",
) -> ModuleRegistryState:
    """Resolve manifests into an installer/runtime registry state."""

    parsed = [
        item if isinstance(item, ModuleManifest) else ModuleManifest.model_validate(item)
        for item in manifests
    ]
    ids = [item.module_id for item in parsed]
    _assert_unique("module", ids)

    by_id = {item.module_id: item for item in parsed}
    selected = (
        set(selected_module_ids)
        if selected_module_ids is not None
        else {item.module_id for item in parsed if item.enabled_by_default}
    )
    unknown = selected - set(by_id)
    if unknown:
        raise ValueError(f"selected modules are not installed: {sorted(unknown)}")

    core_version = Version(civiccore_version)
    for manifest in parsed:
        Version(manifest.version)
        Version(manifest.civiccore_min_version)
        for dependency in manifest.dependencies:
            if dependency.min_version:
                Version(dependency.min_version)

    # Resolve prerequisites before admitting dependants. A visiting node signals
    # a required cycle; propagate the block rather than treating selection as health.
    resolved: dict[str, ModuleRegistryEntry] = {}
    visiting: set[str] = set()

    def resolve(module_id: str) -> ModuleRegistryEntry:
        if module_id in resolved:
            return resolved[module_id]
        manifest = by_id[module_id]
        reason = None
        enabled = module_id in selected
        status: ModuleRegistryStatus = "enabled" if enabled else "disabled"
        if profile not in manifest.install_profiles:
            reason = f"{manifest.name} is not available for the {profile} profile."
        elif enabled and core_version < Version(manifest.civiccore_min_version):
            reason = f"Requires Core {manifest.civiccore_min_version} or newer."
        elif enabled:
            visiting.add(module_id)
            try:
                for dependency in manifest.dependencies:
                    if not dependency.required:
                        continue
                    target = dependency.module_id
                    if target not in selected or target not in by_id:
                        reason = f"Missing required module dependency: {target}."
                    elif target in visiting:
                        reason = f"Required dependency cycle through {target}."
                    elif dependency.min_version and Version(by_id[target].version) < Version(
                        dependency.min_version
                    ):
                        reason = f"Requires {target} {dependency.min_version} or newer."
                    elif not resolve(target).enabled:
                        reason = f"Required module dependency is blocked or disabled: {target}."
                    if reason:
                        break
            finally:
                visiting.remove(module_id)
        if reason:
            enabled, status = False, "blocked"
        entry = ModuleRegistryEntry(
            module_id=module_id,
            name=manifest.name,
            version=manifest.version,
            enabled=enabled,
            locked=False,
            status=status,
            reason=reason,
            manifest=manifest,
        )
        resolved[module_id] = entry
        return entry

    entries = [resolve(manifest.module_id) for manifest in parsed]

    return ModuleRegistryState(
        profile=profile,
        civiccore_version=civiccore_version,
        civiccore_locked=True,
        entries=sorted(entries, key=lambda entry: entry.module_id),
    )


def _assert_unique(label: str, values: list[str]) -> None:
    seen: set[str] = set()
    duplicates = sorted({value for value in values if value in seen or seen.add(value)})
    if duplicates:
        raise ValueError(f"duplicate {label} ids: {', '.join(duplicates)}")


def _validate_windows_runtime_requirements(manifest: ModuleManifest) -> None:
    blocked = [
        requirement.kind
        for requirement in manifest.runtime_requirements
        if requirement.required and requirement.kind in WINDOWS_LOCAL_BLOCKED_RUNTIME_KINDS
    ]
    if blocked:
        blocked_list = ", ".join(sorted(set(blocked)))
        raise ValueError(
            f"{manifest.module_id} cannot require {blocked_list} for the Windows local profile"
        )
    terminal_only = [
        requirement.name
        for requirement in manifest.runtime_requirements
        if requirement.required and requirement.operator_visible and requirement.kind == "terminal"
    ]
    if terminal_only:
        raise ValueError(
            f"{manifest.module_id} exposes terminal-only operator setup: "
            f"{', '.join(sorted(terminal_only))}"
        )
