import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db import Database
from app.main import create_app


@pytest.fixture(scope="session")
def database_url():
    url = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://soup:soup_local_only@127.0.0.1:54329/soup_test")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+asyncpg" or not (parsed.database or "").endswith("_test"):
        pytest.fail("Refusing integration tests: require PostgreSQL database ending in _test")
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
                   cwd=Path(__file__).resolve().parents[1], env=env, check=True)
    return url


@pytest_asyncio.fixture
async def db(database_url):
    database = Database(database_url)
    async with database.engine.begin() as connection:
        await connection.execute(text("TRUNCATE metric_events, batches, runs, projects"))
    yield database
    await database.engine.dispose()


@pytest_asyncio.fixture
async def client(db):
    async with AsyncClient(transport=ASGITransport(app=create_app(db)), base_url="http://test") as client:
        yield client
