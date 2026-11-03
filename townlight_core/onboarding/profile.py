"""Storage-neutral onboarding interview helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class OnboardingField:
    """A tracked onboarding field and the default prompt used to ask for it."""

    name: str
    question: str
    kind: str = "text"


@dataclass(frozen=True)
class OnboardingProgress:
    """Skip-aware progress state for an interview-style onboarding walk."""

    next_field: str | None
    next_question: str | None
    completed_fields: tuple[str, ...]
    skipped_fields: tuple[str, ...]
    all_complete: bool


DEFAULT_PROFILE_FIELDS: tuple[OnboardingField, ...] = (
    OnboardingField("city_name", "What is the name of your city or municipality?"),
    OnboardingField("state", "Which US state is your municipality in? (two-letter code, e.g. CO)"),
    OnboardingField("county", "What county is your municipality in?"),
    OnboardingField(
        "population_band",
        "What is your municipality's approximate population? (Under 5,000 / 5,000-25,000 / 25,000-100,000 / 100,000-500,000 / Over 500,000)",
    ),
    OnboardingField(
        "email_platform",
        "What email platform does your municipality use? (Microsoft 365, Google Workspace, or other)",
    ),
    OnboardingField(
        "has_dedicated_it",
        "Does your municipality have a dedicated IT department? (yes or no)",
        kind="bool",
    ),
    OnboardingField(
        "monthly_request_volume",
        "How many public records requests does your office handle per month on average?",
    ),
)

_YES_ANSWERS = frozenset({"yes", "y", "true", "1"})
_NO_ANSWERS = frozenset({"no", "n", "false", "0"})


def parse_profile_answer(
    field_name: str,
    raw: str | None,
    *,
    fields: Iterable[OnboardingField] = DEFAULT_PROFILE_FIELDS,
) -> object | None:
    """Normalize a text answer into the expected onboarding value."""

    field_map = {field.name: field for field in fields}
    field = field_map.get(field_name)
    if field is None or raw is None:
        return None

    stripped = raw.strip()
    if not stripped:
        return None

    if field.kind == "bool":
        lowered = stripped.lower()
        if lowered in _YES_ANSWERS:
            return True
        if lowered in _NO_ANSWERS:
            return False
        return None

    return stripped


def compute_onboarding_status(
    profile: Mapping[str, Any] | Any | None,
    *,
    fields: Iterable[OnboardingField] = DEFAULT_PROFILE_FIELDS,
) -> str:
    """Return not_started, in_progress, or complete for a profile snapshot."""

    field_list = tuple(fields)
    populated = len(completed_profile_fields(profile, fields=field_list))
    if populated == 0:
        return "not_started"
    if populated == len(field_list):
        return "complete"
    return "in_progress"


def completed_profile_fields(
    profile: Mapping[str, Any] | Any | None,
    *,
    fields: Iterable[OnboardingField] = DEFAULT_PROFILE_FIELDS,
) -> tuple[str, ...]:
    """Return the tracked field names that are currently populated."""

    completed: list[str] = []
    for field in fields:
        value = _get_value(profile, field.name)
        if _is_populated(field, value):
            completed.append(field.name)
    return tuple(completed)


def next_profile_prompt(
    profile: Mapping[str, Any] | Any | None,
    *,
    skipped_fields: Iterable[str] = (),
    fields: Iterable[OnboardingField] = DEFAULT_PROFILE_FIELDS,
) -> OnboardingProgress:
    """Return the next onboarding question plus skip-aware progress state."""

    field_list = tuple(fields)
    skipped = {field_name for field_name in skipped_fields}
    completed: list[str] = []
    next_field: str | None = None
    next_question: str | None = None

    for field in field_list:
        value = _get_value(profile, field.name)
        if _is_populated(field, value):
            completed.append(field.name)
            skipped.discard(field.name)
            continue
        if field.name in skipped:
            continue
        if next_field is None:
            next_field = field.name
            next_question = field.question

    all_complete = len(completed) == len(field_list)
    ordered_skips = tuple(
        field.name
        for field in field_list
        if field.name in skipped and not _is_populated(field, _get_value(profile, field.name))
    )
    return OnboardingProgress(
        next_field=next_field,
        next_question=next_question,
        completed_fields=tuple(completed),
        skipped_fields=ordered_skips,
        all_complete=all_complete,
    )


def _get_value(profile: Mapping[str, Any] | Any | None, field_name: str) -> Any:
    if profile is None:
        return None
    if isinstance(profile, Mapping):
        return profile.get(field_name)
    return getattr(profile, field_name, None)


def _is_populated(field: OnboardingField, value: Any) -> bool:
    if field.kind == "bool":
        return value is not None
    if value is None:
        return False
    return bool(str(value).strip())
