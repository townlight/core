# SPDX-License-Identifier: AGPL-3.0-only
"""Committed claims and heartbeat fencing, adapted from TownReporter job ownership.

Handlers must be cooperative async functions. External authoritative effects need
idempotent receipts and a current claim check; this queue does not promise exactly
once behavior for a remote system that cannot participate in the transaction.
"""

import asyncio
import contextlib
import inspect
from civiccore.platform.task_queue import (
    claim_next_local_task,
    complete_local_task,
    fail_local_task,
    renew_local_task,
    StaleTaskClaim,
)
from civiccore.platform.tasks import TaskRetryPolicy


async def run_leased_task(
    factory, *, handlers, retry_policy=None, lease_seconds=300, max_run_seconds=3600
):
    policy = retry_policy or TaskRetryPolicy()
    if not 1 <= max_run_seconds <= 86400:
        raise ValueError("Invalid task execution deadline")
    async with factory() as session:
        task = await claim_next_local_task(
            session, lease_seconds=lease_seconds, max_attempts=policy.max_attempts
        )
        await session.commit()
    if task is None:
        return None

    async def work():
        handler = handlers.get(task.task_type)
        if handler is None or not inspect.iscoroutinefunction(handler):
            raise ValueError("Leased jobs require a registered cooperative async handler")
        await asyncio.wait_for(handler(task), timeout=max_run_seconds)

    async def heartbeat():
        while True:
            await asyncio.sleep(lease_seconds / 3)
            async with factory() as session:
                await renew_local_task(
                    session, task.task_id, claim_token=task.claim_token, lease_seconds=lease_seconds
                )
                await session.commit()

    active = asyncio.create_task(work())
    beat = asyncio.create_task(heartbeat())
    error = None
    try:
        done, _ = await asyncio.wait((active, beat), return_when=asyncio.FIRST_COMPLETED)
        if beat in done:
            # Includes cancellation, superseded leases and DB failure. Do not
            # overwrite the new owner's state or keep consuming model resources.
            await beat
        await active
    except StaleTaskClaim:
        return None
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:500]}"
    finally:
        for pending in (active, beat):
            if not pending.done():
                pending.cancel()
        for pending in (active, beat):
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await pending
    async with factory() as session:
        try:
            if error:
                result = await fail_local_task(
                    session, task.task_id, error=error, policy=policy, claim_token=task.claim_token
                )
            else:
                result = await complete_local_task(
                    session, task.task_id, claim_token=task.claim_token
                )
            await session.commit()
            return result
        except StaleTaskClaim:
            await session.rollback()
            return None
