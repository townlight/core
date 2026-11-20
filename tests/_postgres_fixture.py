"""Disposable real PostgreSQL databases for hosted Windows and Docker tests."""
from contextlib import contextmanager
import os
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


@contextmanager
def postgres_fixture(image):
    native = os.environ.get("TOWNLIGHT_CORE_TEST_DATABASE_URL")
    if not native:
        from testcontainers.postgres import PostgresContainer
        with PostgresContainer(image) as database:
            yield database
        return
    url = make_url(native)
    assert url.host in {"127.0.0.1", "localhost"}
    assert url.port == 55439 and url.database == "postgres"
    name = "townlight_core_ci_" + uuid.uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    class NativeDatabase:
        def get_connection_url(self):
            return url.set(database=name).render_as_string(hide_password=False)
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        yield NativeDatabase()
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
