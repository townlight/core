"""Small shared search helpers for current Townlight consumers.

This package intentionally ships the smallest honest cross-module surface:
query/text normalization for deterministic substring matching, generic
permission-aware access helpers for search results, and a reciprocal-rank-
fusion helper for hybrid search result merging.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from collections.abc import Hashable, Sequence
from typing import TypeVar


SearchResultId = TypeVar("SearchResultId", bound=Hashable)
AccessRecord = TypeVar("AccessRecord")


def normalize_search_text(text: str) -> str:
    """Normalize search text for case-insensitive, whitespace-stable matching."""
    return " ".join(text.split()).strip().lower()


def normalize_search_query(query: str) -> str:
    """Normalize a free-text query using the same rules as searchable content."""
    return normalize_search_text(query)


def normalize_access_value(value: str) -> str:
    """Normalize a role, tier, or visibility label for deterministic comparison."""
    return value.strip().lower().replace("-", "_")


def normalize_access_values(values: Iterable[str]) -> frozenset[str]:
    """Normalize a collection of access labels, dropping blank values."""
    return frozenset(
        normalized
        for normalized in (normalize_access_value(value) for value in values)
        if normalized
    )


def search_text_matches_query(*, text: str, query: str) -> bool:
    """Return True when the normalized query appears in normalized text."""
    normalized_query = normalize_search_query(query)
    if not normalized_query:
        return True
    return normalized_query in normalize_search_text(text)


def roles_grant_access(
    roles: Iterable[str],
    *,
    allowed_roles: Iterable[str],
) -> bool:
    """Return True when any normalized role appears in the allowed-role set."""
    normalized_roles = normalize_access_values(roles)
    normalized_allowed_roles = normalize_access_values(allowed_roles)
    return not normalized_roles.isdisjoint(normalized_allowed_roles)


def access_level_allows(
    user_level: str,
    record_level: str,
    *,
    level_ranks: Mapping[str, int],
) -> bool:
    """Return True when the user's normalized access level meets the record level."""
    normalized_ranks = {
        normalize_access_value(level): rank
        for level, rank in level_ranks.items()
    }
    normalized_user_level = normalize_access_value(user_level)
    normalized_record_level = normalize_access_value(record_level)
    if normalized_user_level not in normalized_ranks:
        raise ValueError(f"unknown access level: {user_level}")
    if normalized_record_level not in normalized_ranks:
        raise ValueError(f"unknown access level: {record_level}")
    return normalized_ranks[normalized_user_level] >= normalized_ranks[normalized_record_level]


def filter_records_by_access_level(
    records: Iterable[AccessRecord],
    *,
    user_level: str,
    level_ranks: Mapping[str, int],
    access_level_for: Callable[[AccessRecord], str],
) -> list[AccessRecord]:
    """Filter records to the subset visible to a user access level."""
    return [
        record
        for record in records
        if access_level_allows(
            user_level,
            access_level_for(record),
            level_ranks=level_ranks,
        )
    ]


def reciprocal_rank_fusion(
    semantic_results: Sequence[tuple[SearchResultId, float]],
    keyword_results: Sequence[tuple[SearchResultId, float]],
    *,
    k: int = 60,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> list[tuple[SearchResultId, float]]:
    """Fuse semantic and keyword rankings into one weighted result list."""
    scores: dict[SearchResultId, float] = {}

    for rank, (result_id, _) in enumerate(semantic_results):
        scores[result_id] = scores.get(result_id, 0.0) + semantic_weight / (k + rank + 1)

    for rank, (result_id, _) in enumerate(keyword_results):
        scores[result_id] = scores.get(result_id, 0.0) + keyword_weight / (k + rank + 1)

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


__all__ = [
    "access_level_allows",
    "filter_records_by_access_level",
    "normalize_access_value",
    "normalize_access_values",
    "normalize_search_query",
    "normalize_search_text",
    "reciprocal_rank_fusion",
    "roles_grant_access",
    "search_text_matches_query",
]
