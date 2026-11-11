import asyncio
import os
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.errors import APIError


class Database:
    def __init__(self, url: str | None = None):
        self.engine = create_async_engine(
            url or os.environ["DATABASE_URL"],
            pool_size=10, max_overflow=10, pool_timeout=2, pool_pre_ping=True,
            hide_parameters=True, isolation_level="READ COMMITTED",
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def transaction(self, *, snapshot: bool = False):
        # Timeout encloses connection acquisition, statements AND commit.
        try:
            async with asyncio.timeout(5):
                async with self.sessions() as session:
                    async with session.begin():
                        if snapshot:
                            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
                        await session.execute(text("SET LOCAL lock_timeout = '2s'"))
                        await session.execute(text("SET LOCAL statement_timeout = '3s'"))
                        yield session
        except OSError:
            # asyncpg connection establishment can raise native socket errors,
            # outside SQLAlchemy's DBAPIError wrapping. No address/secret echo.
            raise APIError("temporarily_unavailable") from None
        # Caller receives the result only after context exit/commit.
