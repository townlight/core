from __future__ import annotations

from datetime import datetime

import pytest

from townlight_core.scheduling import (
    UTC,
    compute_next_sync_at,
    min_interval_minutes,
    validate_cron_expression,
)


def test_min_interval_minutes_detects_adversarial_burst_schedule() -> None:
    assert min_interval_minutes("*/1 0 * * *", anchor=datetime(2026, 5, 2, tzinfo=UTC)) == 1


def test_validate_cron_expression_requires_standard_syntax_and_five_minute_floor() -> None:
    validate_cron_expression("*/5 * * * *", anchor=datetime(2026, 5, 2, tzinfo=UTC))

    with pytest.raises(ValueError, match="standard 5-field cron syntax"):
        validate_cron_expression("not a cron", anchor=datetime(2026, 5, 2, tzinfo=UTC))

    with pytest.raises(ValueError, match="Minimum allowed interval is 5 minutes"):
        validate_cron_expression("* * * * *", anchor=datetime(2026, 5, 2, tzinfo=UTC))


def test_compute_next_sync_at_uses_epoch_for_never_synced_sources() -> None:
    assert compute_next_sync_at("0 2 * * *", None) == datetime(1970, 1, 1, 2, 0, tzinfo=UTC)


def test_compute_next_sync_at_uses_last_sync_anchor() -> None:
    last_sync = datetime(2026, 5, 1, 2, 1, tzinfo=UTC)
    assert compute_next_sync_at("0 2 * * *", last_sync) == datetime(2026, 5, 2, 2, 0, tzinfo=UTC)


def test_compute_next_sync_at_returns_none_for_missing_schedule() -> None:
    assert compute_next_sync_at("", datetime(2026, 5, 1, tzinfo=UTC)) is None
    assert compute_next_sync_at(None, datetime(2026, 5, 1, tzinfo=UTC)) is None
