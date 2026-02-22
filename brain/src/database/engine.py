from collections.abc import AsyncGenerator

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield an async database session for use as a FastAPI dependency."""
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Verify the database connection is reachable on startup."""
    async with engine.begin() as conn:
        await conn.execute(sa.text("SELECT 1"))
