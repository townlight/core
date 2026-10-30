"""Local task worker entry points for Townlight Core."""

from __future__ import annotations

from civiccore.tasks.artifacts import (
    ArtifactProposal,
    ArtifactRefused,
    ArtifactStore,
    JobArtifact,
    PreparedArtifact,
    SourceBinding,
    accept_artifact,
    artifacts_for_task,
    discard_prepared,
    prepare_artifact,
    resolve_inside_root,
    verify_artifact_file,
)
from civiccore.tasks.registry import get_task_handlers, register_task_handler

__all__ = [
    "ArtifactProposal",
    "ArtifactRefused",
    "ArtifactStore",
    "JobArtifact",
    "PreparedArtifact",
    "SourceBinding",
    "accept_artifact",
    "artifacts_for_task",
    "discard_prepared",
    "get_task_handlers",
    "prepare_artifact",
    "register_task_handler",
    "resolve_inside_root",
    "verify_artifact_file",
]
