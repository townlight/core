"""Unit + integration tests for the Step 3c LLM template engine and resolver.

Engine tests are pure unit tests (no DB). Resolver tests use a fresh
testcontainer Postgres per test (function scope) so each scenario starts from
an empty schema upgraded to townlight_core HEAD — preventing cross-test bleed.

Hard Rule 4a: no test.skip / xfail / inside-test importorskip. The Docker
importorskip at module top is acceptable per the existing test_baseline_idempotency
pattern (Docker is environment, not an SDK we control).
"""

from __future__ import annotations

import asyncio
import sys

# Windows + asyncpg requires SelectorEventLoop, not the default ProactorEventLoop,
# to avoid teardown race conditions during connection close.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import contextlib
import os

import pytest
import pytest_asyncio
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Skip the whole module gracefully if testcontainers is not installed.
testcontainers = pytest.importorskip(
    "testcontainers.postgres",
    reason="testcontainers[postgres] not installed; install dev extras to run resolver tests",
)
PostgresContainer = testcontainers.PostgresContainer

from townlight_core.llm.templates.engine import RenderedPrompt, render_template  # noqa: E402
from townlight_core.llm.templates.exceptions import (  # noqa: E402
    PromptTemplateNotFoundError,
    PromptTemplateRenderError,
)
from townlight_core.llm.templates.models import PromptTemplate  # noqa: E402
from townlight_core.llm.templates.overrides import (  # noqa: E402
    register_template_override,
    unregister_template_override,
)
from townlight_core.llm.templates.resolver import (  # noqa: E402
    TOWNLIGHT_CORE_DEFAULT_APP,
    resolve_template,
)
from townlight_core.migrations.runner import upgrade_to_head  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers (mirrored from tests/test_baseline_idempotency.py)
# ---------------------------------------------------------------------------


def _docker_available() -> bool:
    """Return True if a Docker daemon is reachable; False otherwise."""
    try:
        import docker  # type: ignore[import-untyped]

        docker.from_env().ping()
        return True
    except Exception:
        return False


@contextlib.contextmanager
def _database_url_env(pg_container):
    """Set DATABASE_URL to the testcontainer URL for the scope of the block."""
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = pg_container.get_connection_url()
    try:
        yield
    finally:
        if old_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_url


def _make_template(
    *,
    template_name: str,
    consumer_app: str = "townlight_core",
    is_override: bool = False,
    version: int = 1,
    is_active: bool = True,
    system_prompt: str = "system $name",
    user_prompt_template: str = "user $content",
    purpose: str = "test",
    token_budget: dict | None = None,
) -> PromptTemplate:
    """Construct an unsaved PromptTemplate ORM instance."""
    return PromptTemplate(
        template_name=template_name,
        consumer_app=consumer_app,
        is_override=is_override,
        purpose=purpose,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        token_budget=token_budget,
        version=version,
        is_active=is_active,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def pg_container():
    """Fresh Postgres + pgvector container per test for full isolation."""
    if not _docker_available():
        pytest.skip(
            "Docker daemon not reachable — resolver tests require testcontainers "
            "with a running Docker host. Install Docker Desktop or run in CI."
        )
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        yield pg


@pytest_asyncio.fixture(loop_scope="function")
async def session(pg_container):
    """AsyncSession against a fresh DB upgraded to townlight_core HEAD."""
    # 1. Upgrade schema via the runner (uses DATABASE_URL).
    with _database_url_env(pg_container):
        upgrade_to_head()

    # 2. Build an async engine against the same container.
    sync_url = pg_container.get_connection_url()  # psycopg2 form
    if "+psycopg2" in sync_url:
        async_url = sync_url.replace("postgresql+psycopg2", "postgresql+asyncpg")
    elif sync_url.startswith("postgresql://"):
        async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        async_url = sync_url

    engine = create_async_engine(async_url)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with AsyncSessionLocal() as sess:
            yield sess
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Engine tests (no DB)
# ---------------------------------------------------------------------------


def test_render_template_substitutes_system_and_user():
    """$name and $msg substitute into both system_prompt and user_prompt_template."""
    tmpl = _make_template(
        template_name="greet",
        consumer_app="townlight_core",
        version=3,
        system_prompt="hi $name",
        user_prompt_template="say $msg",
    )

    result = render_template(tmpl, {"name": "alice", "msg": "hello"})

    assert isinstance(result, RenderedPrompt)
    assert result.system == "hi alice"
    assert result.user == "say hello"
    assert result.template_name == "greet"
    assert result.consumer_app == "townlight_core"
    assert result.version == 3


def test_render_template_missing_variable_raises_actionable():
    """Missing variable raises PromptTemplateRenderError with the variable name."""
    tmpl = _make_template(
        template_name="needs_missing",
        system_prompt="ok",
        user_prompt_template="value=$missing",
    )

    with pytest.raises(PromptTemplateRenderError) as excinfo:
        render_template(tmpl, {})

    err = excinfo.value
    assert err.missing_variable == "missing"
    assert "missing" in str(err)
    assert "needs_missing" in str(err)


def test_render_template_no_variables_works_when_template_has_none():
    """Templates with no $-references render verbatim from an empty vars dict."""
    tmpl = _make_template(
        template_name="static",
        system_prompt="just a system line",
        user_prompt_template="just a user line",
    )

    result = render_template(tmpl, {})

    assert result.system == "just a system line"
    assert result.user == "just a user line"


def test_render_template_supports_braced_form():
    """${var} substitutes the same way $var does (string.Template behavior)."""
    tmpl = _make_template(
        template_name="braced",
        system_prompt="prefix-${who}-suffix",
        user_prompt_template="hello",
    )

    result = render_template(tmpl, {"who": "world"})

    assert result.system == "prefix-world-suffix"


def test_render_template_does_not_collide_with_json_braces():
    """Literal JSON braces are preserved — string.Template uses $, not {}."""
    json_body = 'Return JSON like {"key": "value", "n": 1}'
    tmpl = _make_template(
        template_name="json_body",
        system_prompt=json_body,
        user_prompt_template="$instruction",
    )

    result = render_template(tmpl, {"instruction": "do it"})

    assert result.system == json_body
    assert '{"key": "value", "n": 1}' in result.system
    assert result.user == "do it"


# ---------------------------------------------------------------------------
# Resolver tests (testcontainer Postgres)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolver_returns_townlight_core_default_when_only_default_exists(session):
    """A townlight_core default is returned when no app-specific override exists."""
    session.add(
        _make_template(
            template_name="t1",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            is_override=False,
            is_active=True,
        )
    )
    await session.commit()

    found = await resolve_template(
        session, template_name="t1", consumer_app="townlight_records"
    )

    assert found.template_name == "t1"
    assert found.consumer_app == TOWNLIGHT_CORE_DEFAULT_APP
    assert found.is_override is False


@pytest.mark.asyncio
async def test_resolver_app_override_wins_over_townlight_core_default(session):
    """When an app override exists, it wins over the townlight_core default."""
    session.add(
        _make_template(
            template_name="t2",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            is_override=False,
            system_prompt="DEFAULT system",
        )
    )
    session.add(
        _make_template(
            template_name="t2",
            consumer_app="townlight_records",
            is_override=True,
            system_prompt="OVERRIDE system",
        )
    )
    await session.commit()

    found = await resolve_template(
        session, template_name="t2", consumer_app="townlight_records"
    )

    assert found.consumer_app == "townlight_records"
    assert found.is_override is True
    assert found.system_prompt == "OVERRIDE system"


@pytest.mark.asyncio
async def test_resolver_townlight_core_app_skips_step1(session):
    """When consumer_app == 'townlight_core', step 1 (override lookup) is skipped.

    Even if a townlight_core + is_override=True row exists (operator misconfiguration),
    a consumer_app='townlight_core' resolution returns the canonical default
    (is_override=False) row.
    """
    # Misplaced override row (same app as the default — operator slip).
    session.add(
        _make_template(
            template_name="t3",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            is_override=True,
            version=1,
            system_prompt="WEIRD override-on-townlight_core",
        )
    )
    # Canonical default.
    session.add(
        _make_template(
            template_name="t3",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            is_override=False,
            version=2,
            system_prompt="canonical default",
        )
    )
    await session.commit()

    found = await resolve_template(
        session, template_name="t3", consumer_app=TOWNLIGHT_CORE_DEFAULT_APP
    )

    assert found.is_override is False
    assert found.system_prompt == "canonical default"


@pytest.mark.asyncio
async def test_resolver_inactive_templates_ignored(session):
    """is_active=False rows are not eligible — resolver raises NotFound."""
    session.add(
        _make_template(
            template_name="t4",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            is_active=False,
        )
    )
    await session.commit()

    with pytest.raises(PromptTemplateNotFoundError):
        await resolve_template(
            session, template_name="t4", consumer_app="townlight_records"
        )


@pytest.mark.asyncio
async def test_resolver_highest_version_wins(session):
    """Among active rows for the same key, the highest version is returned."""
    session.add(
        _make_template(
            template_name="t5",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            version=1,
            is_active=True,
            system_prompt="v1",
        )
    )
    session.add(
        _make_template(
            template_name="t5",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            version=2,
            is_active=True,
            system_prompt="v2",
        )
    )
    await session.commit()

    found = await resolve_template(
        session, template_name="t5", consumer_app="townlight_records"
    )

    assert found.version == 2
    assert found.system_prompt == "v2"


@pytest.mark.asyncio
async def test_resolver_inactive_higher_version_skipped_active_lower_returned(session):
    """An inactive higher version is skipped; the active lower version wins."""
    session.add(
        _make_template(
            template_name="t6",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            version=1,
            is_active=True,
            system_prompt="v1-active",
        )
    )
    session.add(
        _make_template(
            template_name="t6",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            version=2,
            is_active=False,
            system_prompt="v2-inactive",
        )
    )
    await session.commit()

    found = await resolve_template(
        session, template_name="t6", consumer_app="townlight_records"
    )

    assert found.version == 1
    assert found.system_prompt == "v1-active"


@pytest.mark.asyncio
async def test_resolver_missing_template_raises_actionable_error(session):
    """Empty DB raises NotFound carrying both template_name and consumer_app."""
    with pytest.raises(PromptTemplateNotFoundError) as excinfo:
        await resolve_template(
            session, template_name="nope", consumer_app="townlight_records"
        )

    err = excinfo.value
    # Constructor exposes these attributes per the spec.
    assert err.template_name == "nope"
    assert err.consumer_app == "townlight_records"
    msg = str(err)
    assert "nope" in msg
    assert "townlight_records" in msg


def test_resolver_uses_template_name_not_old_name_column():
    """Sanity check: ORM column is named template_name, not name (ADR rename)."""
    cols = inspect(PromptTemplate).columns.keys()
    assert "template_name" in cols
    assert "name" not in cols


@pytest.mark.asyncio
async def test_resolver_uses_consumer_app_not_null_fallback(session):
    """The townlight_core default uses consumer_app='townlight_core', NOT IS NULL.

    Per ADR-0004, the legacy IS NULL fallback is removed; the default tier
    is keyed on the literal string 'townlight_core'.
    """
    session.add(
        _make_template(
            template_name="t8",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,  # literal "townlight_core"
            is_override=False,
            is_active=True,
        )
    )
    await session.commit()

    # Resolution from a different consumer_app finds the townlight_core default.
    found = await resolve_template(
        session, template_name="t8", consumer_app="townlight_records"
    )

    assert found.consumer_app == TOWNLIGHT_CORE_DEFAULT_APP
    # Belt-and-suspenders: the column value is non-null.
    assert found.consumer_app is not None


# ---------------------------------------------------------------------------
# Code-level override resolution (ADR-0004 §7 step 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolver_db_override_wins_over_code_override(session):
    """Per ADR-0004 §7: DB app override takes precedence over code-level
    override (operators must hot-fix prompts in production without redeploy)."""
    # Register code override
    code_tmpl = _make_template(
        template_name="contested",
        consumer_app="townlight_records",
        is_override=True,
        system_prompt="CODE OVERRIDE",
        user_prompt_template="from code",
    )
    register_template_override(
        consumer_app="townlight_records",
        template_name="contested",
        template=code_tmpl,
    )
    try:
        # Persist DB override (different prompt body)
        db_override = _make_template(
            template_name="contested",
            consumer_app="townlight_records",
            is_override=True,
            is_active=True,
            system_prompt="DB OVERRIDE",
            user_prompt_template="from db",
        )
        session.add(db_override)
        await session.commit()
        # Resolver returns the DB row, not the code override
        resolved = await resolve_template(
            session,
            template_name="contested",
            consumer_app="townlight_records",
        )
        assert resolved.system_prompt == "DB OVERRIDE"
    finally:
        unregister_template_override(
            consumer_app="townlight_records", template_name="contested"
        )


@pytest.mark.asyncio
async def test_resolver_code_override_wins_over_townlight_core_default(session):
    """No DB app override; code-level override beats townlight_core default."""
    code_tmpl = _make_template(
        template_name="t1",
        consumer_app="townlight_records",
        is_override=True,
        system_prompt="CODE OVERRIDE",
        user_prompt_template="x",
    )
    register_template_override(
        consumer_app="townlight_records",
        template_name="t1",
        template=code_tmpl,
    )
    try:
        # townlight_core default in DB
        townlight_core_default = _make_template(
            template_name="t1",
            consumer_app="townlight_core",
            is_override=False,
            is_active=True,
            system_prompt="TOWNLIGHT_CORE DEFAULT",
            user_prompt_template="y",
        )
        session.add(townlight_core_default)
        await session.commit()
        resolved = await resolve_template(
            session,
            template_name="t1",
            consumer_app="townlight_records",
        )
        assert resolved.system_prompt == "CODE OVERRIDE"
    finally:
        unregister_template_override(
            consumer_app="townlight_records", template_name="t1"
        )


@pytest.mark.asyncio
async def test_resolver_townlight_core_app_skips_code_override(session):
    """consumer_app='townlight_core' skips both step 1 (DB override) and step 2
    (code override). townlight_core owns its own defaults."""
    code_tmpl = _make_template(
        template_name="t2",
        consumer_app="townlight_core",
        system_prompt="CODE",
        user_prompt_template="x",
    )
    # Register a code override under townlight_core (operator could theoretically
    # do this; resolver must ignore it for consumer_app='townlight_core' callers).
    register_template_override(
        consumer_app="townlight_core",
        template_name="t2",
        template=code_tmpl,
    )
    try:
        # townlight_core DB default
        db_default = _make_template(
            template_name="t2",
            consumer_app="townlight_core",
            is_active=True,
            system_prompt="DB DEFAULT",
            user_prompt_template="y",
        )
        session.add(db_default)
        await session.commit()
        resolved = await resolve_template(
            session, template_name="t2", consumer_app="townlight_core"
        )
        # Returns DB default; ignores any registered code override under townlight_core
        assert resolved.system_prompt == "DB DEFAULT"
    finally:
        unregister_template_override(
            consumer_app="townlight_core", template_name="t2"
        )


@pytest.mark.asyncio
async def test_resolver_code_override_alone_is_resolvable(session):
    """No DB row at all; code override is the only source. Resolver returns it."""
    code_tmpl = _make_template(
        template_name="solo",
        consumer_app="townlight_records",
        is_override=True,
        system_prompt="ONLY IN CODE",
        user_prompt_template="x",
    )
    register_template_override(
        consumer_app="townlight_records",
        template_name="solo",
        template=code_tmpl,
    )
    try:
        # Empty DB; only the code override exists.
        resolved = await resolve_template(
            session, template_name="solo", consumer_app="townlight_records"
        )
        assert resolved.system_prompt == "ONLY IN CODE"
    finally:
        unregister_template_override(
            consumer_app="townlight_records", template_name="solo"
        )


# ---------------------------------------------------------------------------
# Cross / E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolver_then_render_e2e(session):
    """Resolve a template from the DB, then render it through the engine."""
    session.add(
        _make_template(
            template_name="e2e",
            consumer_app=TOWNLIGHT_CORE_DEFAULT_APP,
            system_prompt="You are a $role.",
            user_prompt_template="Process this: $user_input",
            version=1,
        )
    )
    await session.commit()

    tmpl = await resolve_template(
        session, template_name="e2e", consumer_app="townlight_records"
    )
    rendered = render_template(
        tmpl, {"role": "summarizer", "user_input": "the meeting minutes"}
    )

    assert rendered.system == "You are a summarizer."
    assert rendered.user == "Process this: the meeting minutes"
    assert rendered.template_name == "e2e"
    assert rendered.consumer_app == TOWNLIGHT_CORE_DEFAULT_APP
    assert rendered.version == 1
