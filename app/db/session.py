from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    """Put every SQLite connection into WAL with a bounded wait for the write lock.

    Both pragmas address the same failure: SQLite's default journal mode takes an
    exclusive lock on the whole database for a write, and a connection that finds the
    database busy gives up immediately with "database is locked" rather than waiting.
    That is a real risk here because logging a meal writes while a request on another
    connection may still be reading.

    * ``journal_mode=WAL`` lets readers proceed during a write instead of blocking.
      It is stored in the database file, so it persists — reapplying it per connection
      is a cheap no-op that also covers a freshly created database.
    * ``busy_timeout`` is per connection and is *not* persisted, so it has to be set
      every time. Without it the timeout is zero: no waiting, straight to an error.
      Five seconds is far longer than any write here takes.

    Guarded on the dialect because the engine URL is configurable and the choice to
    stay on SQLite is explicitly provisional — these statements are not valid on
    Postgres, and this would otherwise fail at connect time on the day it changes.
    """
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
