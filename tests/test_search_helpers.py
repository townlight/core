from __future__ import annotations

import uuid

from townlight_core.search import (
    access_level_allows,
    filter_records_by_access_level,
    normalize_access_value,
    normalize_access_values,
    normalize_search_query,
    normalize_search_text,
    reciprocal_rank_fusion,
    roles_grant_access,
    search_text_matches_query,
)


def test_normalize_search_text_collapses_case_and_whitespace() -> None:
    assert normalize_search_text("  Budget\tMeeting \n Packet  ") == "budget meeting packet"


def test_normalize_search_query_uses_same_rules_as_text() -> None:
    assert normalize_search_query("  Closed   Session ") == "closed session"


def test_search_text_matches_query_is_case_insensitive_and_whitespace_stable() -> None:
    assert search_text_matches_query(
        text="Closed   Cybersecurity Briefing",
        query="  cybersecurity   briefing ",
    )


def test_search_text_matches_query_treats_blank_query_as_match() -> None:
    assert search_text_matches_query(text="Anything", query="   ")


def test_normalize_access_value_collapses_hyphens_case_and_whitespace() -> None:
    assert normalize_access_value("  City-Attorney ") == "city_attorney"


def test_normalize_access_values_drops_blank_entries() -> None:
    assert normalize_access_values([" archive_reader ", "", "Clerk-Admin"]) == {
        "archive_reader",
        "clerk_admin",
    }


def test_roles_grant_access_matches_when_any_allowed_role_is_present() -> None:
    assert roles_grant_access(
        ["meeting_editor", "City-Attorney"],
        allowed_roles={"archive_reader", "city_attorney"},
    )


def test_access_level_allows_uses_normalized_rank_map() -> None:
    level_ranks = {"public": 0, "staff": 1, "attorney": 2, "privileged": 3}
    assert access_level_allows("staff", "attorney", level_ranks=level_ranks) is False
    assert access_level_allows("privileged", "attorney", level_ranks=level_ranks) is True


def test_filter_records_by_access_level_returns_only_visible_records() -> None:
    level_ranks = {"public": 0, "staff": 1, "attorney": 2, "privileged": 3}
    records = [
        {"id": "public-1", "tier": "public"},
        {"id": "staff-1", "tier": "staff"},
        {"id": "memo-1", "tier": "privileged"},
    ]
    visible = filter_records_by_access_level(
        records,
        user_level="staff",
        level_ranks=level_ranks,
        access_level_for=lambda record: record["tier"],
    )
    assert visible == [
        {"id": "public-1", "tier": "public"},
        {"id": "staff-1", "tier": "staff"},
    ]


def test_reciprocal_rank_fusion_combines_both_result_sets() -> None:
    result_a, result_b, result_c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    fused = reciprocal_rank_fusion(
        [(result_a, 0.1), (result_b, 0.2)],
        [(result_b, 0.9), (result_c, 0.8)],
    )

    fused_ids = [result_id for result_id, _ in fused]
    assert fused_ids == [result_b, result_a, result_c]
    assert all(score > 0 for _, score in fused)


def test_reciprocal_rank_fusion_allows_empty_inputs() -> None:
    assert reciprocal_rank_fusion([], []) == []
