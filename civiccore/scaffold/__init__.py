# SPDX-License-Identifier: AGPL-3.0-only
"""Townlight Core module scaffold.

The historical CO-7 deferral (docs/adr/ADR-0003-defer-civiccore-scaffold.md) is
preserved verbatim. ADR-0007 resuming scaffold extraction records the actual new
contract: a working generator for one minimal module project, tested in
isolation. Only ``generate_module_project``, ``plan_module_project`` and
``ModuleSpec`` are promised; the reserved placeholder text that once said "No
downstream module may depend on this namespace until scaffold behavior ships in a
versioned Townlight Core release artifact" remains the standing rule for consumers
— this candidate is not a release artifact, so downstream modules must still not
depend on it.
"""

from __future__ import annotations

from civiccore.scaffold.cli import main as main
from civiccore.scaffold.project import (
    GENERATOR_VERSION,
    GenerationResult,
    PlannedFile,
    ProjectPlan,
    generate_module_project,
    plan_module_project,
)
from civiccore.scaffold.spec import (
    InvalidModuleSpecError,
    ModuleSpec,
    PathContainmentError,
    ScaffoldError,
    ScaffoldOptions,
    TargetExistsError,
    UnsafeTargetError,
)

__all__ = [
    "GENERATOR_VERSION",
    "GenerationResult",
    "InvalidModuleSpecError",
    "ModuleSpec",
    "PathContainmentError",
    "PlannedFile",
    "ProjectPlan",
    "ScaffoldError",
    "ScaffoldOptions",
    "TargetExistsError",
    "UnsafeTargetError",
    "generate_module_project",
    "main",
    "plan_module_project",
]
