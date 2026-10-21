"""CLI worker for the Townlight Core PostgreSQL-backed local task queue."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import os
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from civiccore.platform.task_queue import run_one_local_task
from civiccore.platform.tasks import TaskRetryPolicy
from civiccore.tasks.registry import get_task_handlers


def _async_database_url(url: str) -> str:
    if "+psycopg2" in url:
        return url.replace("postgresql+psycopg2", "postgresql+asyncpg")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _load_handler_modules(raw_modules: str | None) -> None:
    if not raw_modules:
        return
    for module_name in [item.strip() for item in raw_modules.split(",") if item.strip()]:
        importlib.import_module(module_name)


async def _run_worker(args: argparse.Namespace) -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for civiccore.tasks.worker")
    _load_handler_modules(os.environ.get("CIVICCORE_TASK_HANDLER_MODULES"))
    handlers = get_task_handlers()

    engine = create_async_engine(_async_database_url(database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    retry_policy = TaskRetryPolicy(
        max_attempts=args.max_attempts,
        base_delay_seconds=args.base_delay_seconds,
        max_delay_seconds=args.max_delay_seconds,
    )

    try:
        while True:
            async with session_factory() as session:
                task = await run_one_local_task(
                    session,
                    handlers=handlers,
                    retry_policy=retry_policy,
                )
                await session.commit()
            if args.once:
                return 0
            if task is None:
                await asyncio.sleep(args.poll_seconds)
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Townlight Core local task worker.")
    parser.add_argument("--backend", choices=["postgres"], default="postgres")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--base-delay-seconds", type=int, default=30)
    parser.add_argument("--max-delay-seconds", type=int, default=3600)
    args = parser.parse_args(argv)
    return asyncio.run(_run_worker(args))


if __name__ == "__main__":  # pragma: no cover - exercised through CLI smoke
    raise SystemExit(main())
