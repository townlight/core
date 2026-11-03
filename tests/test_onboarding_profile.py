from __future__ import annotations

from townlight_core.onboarding import (
    DEFAULT_PROFILE_FIELDS,
    completed_profile_fields,
    compute_onboarding_status,
    next_profile_prompt,
    parse_profile_answer,
)


def test_parse_profile_answer_normalizes_boolean_fields() -> None:
    assert parse_profile_answer("has_dedicated_it", "Yes") is True
    assert parse_profile_answer("has_dedicated_it", "n") is False
    assert parse_profile_answer("has_dedicated_it", "maybe") is None


def test_parse_profile_answer_trims_text_fields() -> None:
    assert parse_profile_answer("city_name", "  Sampleville  ") == "Sampleville"
    assert parse_profile_answer("city_name", "   ") is None


def test_compute_onboarding_status_tracks_empty_partial_and_complete_profiles() -> None:
    assert compute_onboarding_status(None) == "not_started"
    assert compute_onboarding_status({"city_name": "Sampleville"}) == "in_progress"

    complete_profile = {
        "city_name": "Sampleville",
        "state": "CO",
        "county": "Jefferson",
        "population_band": "25,000-100,000",
        "email_platform": "Microsoft 365",
        "has_dedicated_it": True,
        "monthly_request_volume": "5-20",
    }
    assert compute_onboarding_status(complete_profile) == "complete"


def test_completed_profile_fields_accepts_mapping_or_object() -> None:
    mapping_result = completed_profile_fields({"city_name": "Sampleville", "state": "CO"})
    assert mapping_result == ("city_name", "state")

    profile_object = type("Profile", (), {"city_name": "Sampleville", "state": "CO"})()
    object_result = completed_profile_fields(profile_object)
    assert object_result == ("city_name", "state")


def test_next_profile_prompt_honors_skipped_fields_and_preserves_order() -> None:
    progress = next_profile_prompt(
        {"city_name": "Sampleville"},
        skipped_fields=("state",),
    )

    assert progress.completed_fields == ("city_name",)
    assert progress.skipped_fields == ("state",)
    assert progress.next_field == "county"
    assert progress.next_question == DEFAULT_PROFILE_FIELDS[2].question
    assert progress.all_complete is False


def test_next_profile_prompt_marks_all_complete_only_when_every_field_is_populated() -> None:
    profile = {
        "city_name": "Sampleville",
        "state": "CO",
        "county": "Jefferson",
        "population_band": "25,000-100,000",
        "email_platform": "Microsoft 365",
        "has_dedicated_it": False,
        "monthly_request_volume": "5-20",
    }

    progress = next_profile_prompt(profile)

    assert progress.all_complete is True
    assert progress.next_field is None
    assert progress.next_question is None
    assert progress.skipped_fields == ()
