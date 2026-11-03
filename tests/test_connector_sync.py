from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from townlight_core.connectors import (
    SyncCircuitPolicy,
    SyncCircuitState,
    SyncRetryExhausted,
    SyncRetryPolicy,
    SyncRunResult,
    apply_sync_run_result,
    build_sync_operator_status,
    build_sync_source_status,
    compute_retry_delay,
    compute_sync_health_status,
    with_http_retry,
)


def test_apply_sync_run_result_opens_circuit_after_full_failure_threshold() -> None:
    state = SyncCircuitState(connector="legistar", source_name="Legistar production")
    now = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)

    for _ in range(5):
        state = apply_sync_run_result(
            state,
            SyncRunResult(records_discovered=1, records_succeeded=0, records_failed=1),
            now=now,
        )

    assert state.sync_paused is True
    assert state.sync_paused_at == now
    assert state.last_error_at == now
    assert state.last_sync_status == "failed"
    assert state.sync_paused_reason == "Circuit open after 5 consecutive full-run failures."
    assert compute_sync_health_status(state) == "circuit_open"


def test_apply_sync_run_result_uses_short_grace_period_threshold() -> None:
    state = SyncCircuitState(
        connector="granicus",
        source_name="Granicus production",
        sync_paused_reason="grace_period",
    )

    state = apply_sync_run_result(
        state,
        SyncRunResult(records_discovered=1, records_succeeded=0, records_failed=1),
    )
    assert state.sync_paused is False

    state = apply_sync_run_result(
        state,
        SyncRunResult(records_discovered=1, records_succeeded=0, records_failed=1),
    )
    assert state.sync_paused is True
    assert state.sync_paused_reason == "Circuit open after 2 consecutive full-run failures."


def test_success_resets_failure_counter_and_partial_status_preserves_operator_visibility() -> None:
    state = SyncCircuitState(
        connector="primegov",
        source_name="PrimeGov production",
        consecutive_failure_count=4,
        active_failure_count=2,
        sync_paused_reason="grace_period",
    )

    updated = apply_sync_run_result(
        state,
        SyncRunResult(records_discovered=3, records_succeeded=2, records_failed=1),
    )

    assert updated.consecutive_failure_count == 0
    assert updated.last_sync_status == "partial"
    assert updated.sync_paused is False
    assert updated.sync_paused_reason is None
    assert updated.active_failure_count == 2
    assert updated.health_status == "degraded"


def test_build_sync_operator_status_returns_actionable_fix_copy() -> None:
    status = build_sync_operator_status(
        SyncCircuitState(
            connector="legistar",
            source_name="Legistar production",
            active_failure_count=1,
        )
    )

    assert status.health_status == "degraded"
    assert "Legistar production live sync is degraded." == status.message
    assert "circuit opens after 5 consecutive full-run failures" in status.fix
    assert status.public_dict()["fix"] == status.fix


def test_compute_retry_delay_honors_retry_after_cap_without_jitter() -> None:
    policy = SyncRetryPolicy(jitter_factor=0.2, retry_after_cap_seconds=10.0)

    assert compute_retry_delay(1, policy=policy, random_value=0.5) == 2.0
    assert compute_retry_delay(
        0,
        retry_after_seconds=4.0,
        policy=policy,
        random_value=1.0,
    ) == 4.0
    assert compute_retry_delay(0, retry_after_seconds=11.0, policy=policy) == 10.0


@pytest.mark.asyncio
async def test_with_http_retry_retries_429_then_returns_success() -> None:
    responses = [
        httpx.Response(429, headers={"Retry-After": "2"}),
        httpx.Response(200),
    ]
    sleeps: list[float] = []

    async def action() -> httpx.Response:
        return responses.pop(0)

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    response = await with_http_retry(
        action,
        policy=SyncRetryPolicy(jitter_factor=0),
        sleep=sleep,
    )

    assert response.status_code == 200
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_with_http_retry_raises_actionable_error_after_exhaustion() -> None:
    async def action() -> httpx.Response:
        return httpx.Response(503)

    async def sleep(_delay: float) -> None:
        return None

    with pytest.raises(SyncRetryExhausted, match="Server error 503 after 2 attempt"):
        await with_http_retry(
            action,
            policy=SyncRetryPolicy(max_attempts=2, jitter_factor=0),
            sleep=sleep,
        )


def test_custom_sync_circuit_policy_changes_operator_copy_threshold() -> None:
    status = build_sync_operator_status(
        SyncCircuitState(
            connector="custom",
            source_name="Custom vendor",
            consecutive_failure_count=1,
        ),
        policy=SyncCircuitPolicy(full_failure_threshold=7),
    )

    assert status.health_status == "degraded"
    assert "after 7 consecutive full-run failures" in status.fix


def test_build_sync_source_status_includes_health_copy_and_next_run() -> None:
    status = build_sync_source_status(
        SyncCircuitState(
            connector="rest_api",
            source_name="Records vendor API",
            active_failure_count=2,
            last_sync_status="partial",
        ),
        sync_schedule="0 2 * * *",
        last_sync_at=None,
    )

    assert status.health_status == "degraded"
    assert status.active_failure_count == 2
    assert status.last_sync_status == "partial"
    assert status.next_sync_at == datetime(1970, 1, 1, 2, 0, tzinfo=UTC)
    assert status.public_dict()["fix"] == status.fix


def test_build_sync_source_status_suppresses_next_run_when_paused() -> None:
    status = build_sync_source_status(
        SyncCircuitState(
            connector="legistar",
            source_name="Legistar production",
            sync_paused=True,
            sync_paused_reason="Circuit open after 5 consecutive full-run failures.",
        ),
        sync_schedule="*/5 * * * *",
        last_sync_at=datetime(2026, 5, 2, tzinfo=UTC),
    )

    assert status.health_status == "circuit_open"
    assert status.next_sync_at is None
    assert "correct the vendor credentials or endpoint" in status.fix
