"""
backend/db/session.py
─────────────────────
Database session management.

LESSON — Why async sessions?
─────────────────────────────
FastAPI is async. If we used synchronous SQLAlchemy sessions, every DB
query would block the event loop, negating the performance benefit of async.

SQLAlchemy's `async_sessionmaker` gives us sessions where every operation
is awaitable:

    async with get_session() as session:
        result = await session.execute(select(EvalItem))

LESSON — What is a "session"?
A session is a unit of work against the database. It:
  1. Tracks which objects you've loaded/modified
  2. Buffers changes until you call `session.commit()`
  3. Rolls back automatically if an exception occurs (when used as context manager)

LESSON — Connection pools:
The engine holds a pool of database connections. Rather than opening a new
connection per request (slow), it reuses existing ones. The pool size is
configurable; the defaults are fine for SQLite but tune for Postgres in prod.
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings
from backend.db.models import Base

# The engine is the low-level connection factory.
# echo=True prints all SQL to stdout — useful for debugging, turn off in prod.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    # SQLite-specific: allow use from multiple async tasks
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# Session factory — call this to get a new session
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # don't expire objects after commit (saves re-queries)
)


async def init_db():
    """
    Create all tables if they don't exist.
    Called once at application startup.

    In production you'd use Alembic migrations instead of create_all(),
    because create_all() can't handle schema changes to existing tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session():
    """
    Async context manager that yields a database session.

    Usage:
        async with get_session() as session:
            session.add(some_object)
            await session.commit()

    The session is automatically closed (and rolled back on error)
    when the `with` block exits.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session():
    """
    FastAPI dependency version — yields a session per request.

    Usage in a route:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
