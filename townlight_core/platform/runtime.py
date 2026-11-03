"""Runtime action contracts for the Windows local desktop shell."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from townlight_core.platform.modules import ModuleRegistryState

RuntimeAction = Literal[
    "install",
    "first_run",
    "health_check",
    "repair",
    "backup",
    "restore",
    "uninstall",
    "module_install",
    "module_disable",
    "model_download",
]
RuntimeActionStatus = Literal["pending", "running", "succeeded", "needs_action", "failed", "blocked"]


class RuntimeActionResult(BaseModel):
    """Plain-English result returned by installer/runtime APIs."""

    model_config = ConfigDict(extra="forbid")

    action: RuntimeAction
    status: RuntimeActionStatus
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    next_action: str | None = Field(default=None, min_length=1)
    evidence: dict[str, str | int | bool | None] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class LocalRuntimeProfile(BaseModel):
    """Resolved local runtime profile for one installed city."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(min_length=1)
    city_name: str = Field(min_length=1)
    data_root: Path
    backup_root: Path
    module_registry: ModuleRegistryState
    model_provider: str = "ollama"
    local_only: bool = True
    network_allowed_for: list[str] = Field(default_factory=list)

    @field_validator("network_allowed_for")
    @classmethod
    def validate_network_reasons(cls, value: list[str]) -> list[str]:
        for reason in value:
            if not reason.strip():
                raise ValueError("network_allowed_for entries cannot be blank")
        return value
