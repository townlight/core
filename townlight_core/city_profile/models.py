"""Local-first city profile models for Townlight Core deployments."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LOCAL_LLM_PROVIDERS = frozenset({"ollama", "local", "llamacpp", "none"})
OUTBOUND_LLM_PROVIDERS = frozenset({"openai", "anthropic"})


class DepartmentProfile(BaseModel):
    """A city department surfaced during local onboarding."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    public_email: str | None = Field(default=None, min_length=3)
    public_phone: str | None = Field(default=None, min_length=3)


class DeploymentProfile(BaseModel):
    """Deployment posture for a profile without acting as an installer."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["local_demo", "local", "self_hosted"] = "local_demo"
    allow_outbound_services: bool = False


class ModuleEnablement(BaseModel):
    """Per-module enablement flags and local configuration metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


class CityProfile(BaseModel):
    """Local city profile loaded from trusted JSON/YAML configuration."""

    model_config = ConfigDict(extra="forbid")

    city_name: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    departments: list[DepartmentProfile] = Field(default_factory=list)
    enabled_modules: list[ModuleEnablement] = Field(default_factory=list)
    default_llm_provider: str = "ollama"
    file_drop_roots: list[Path] = Field(default_factory=list)
    public_contact: dict[str, str] = Field(default_factory=dict)
    deployment: DeploymentProfile = Field(default_factory=DeploymentProfile)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"timezone must be a valid IANA timezone, got {value!r}") from exc
        return value

    @field_validator("file_drop_roots", mode="before")
    @classmethod
    def validate_file_drop_roots(cls, value: Any) -> Any:
        roots = value if isinstance(value, list) else [value]
        for root in roots:
            raw_root = str(root)
            parsed = urlparse(raw_root)
            if "://" in raw_root and parsed.scheme != "file":
                raise ValueError(
                    "file_drop_roots must be local filesystem paths, not outbound URLs"
                )
        return value

    @field_validator("default_llm_provider")
    @classmethod
    def normalize_llm_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("default_llm_provider cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_local_first_defaults(self) -> CityProfile:
        if (
            self.default_llm_provider in OUTBOUND_LLM_PROVIDERS
            and not self.deployment.allow_outbound_services
        ):
            raise ValueError(
                "default_llm_provider requires outbound services; set "
                "deployment.allow_outbound_services=true to opt in explicitly"
            )
        return self


def load_city_profile(path: str | Path) -> CityProfile:
    """Load a city profile from JSON, or YAML when PyYAML is installed."""

    profile_path = Path(path)
    suffix = profile_path.suffix.lower()
    raw = profile_path.read_text(encoding="utf-8")

    if suffix == ".json":
        data = json.loads(raw)
    elif suffix in {".yaml", ".yml"}:
        data = _load_yaml(raw)
    else:
        raise ValueError("city profile must be a .json, .yaml, or .yml file")

    if not isinstance(data, dict):
        raise ValueError("city profile file must contain an object at the top level")

    return CityProfile.model_validate(data)


def _load_yaml(raw: str) -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on optional local install
        raise ValueError(
            "YAML city profiles require PyYAML. Use JSON or install PyYAML to load YAML."
        ) from exc

    return yaml.safe_load(raw)


__all__ = [
    "CityProfile",
    "DepartmentProfile",
    "DeploymentProfile",
    "ModuleEnablement",
    "load_city_profile",
]
