"""Read-only PostgreSQL/pgvector preflight: python -m ai_engine.app.db.check."""

import sys

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from .database import engine


class DatabasePrerequisiteError(RuntimeError):
    """The database needs operator setup before AI migrations can run."""


def check_pgvector(connection: Connection) -> str:
    """Return the enabled vector extension version without changing the database."""
    version = connection.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    ).scalar_one_or_none()
    if version is not None:
        return version

    available = connection.execute(
        text("SELECT default_version FROM pg_available_extensions WHERE name = 'vector'")
    ).scalar_one_or_none()
    if available is None:
        raise DatabasePrerequisiteError(
            "pgvector is not installed on the PostgreSQL server. Install pgvector "
            "for that PostgreSQL version, then enable it in the configured database."
        )
    raise DatabasePrerequisiteError(
        "pgvector is available but not enabled in the configured database. "
        "Ask the database owner to run CREATE EXTENSION IF NOT EXISTS vector; "
        "in that database before running AI migrations."
    )


def main() -> int:
    try:
        with engine.connect() as connection:
            version = check_pgvector(connection)
    except DatabasePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SQLAlchemyError:
        # Driver errors may contain connection parameters; do not echo credentials.
        print(
            "Database preflight failed. Check POSTGRES_* settings, credentials, "
            "and PostgreSQL connectivity.",
            file=sys.stderr,
        )
        return 1
    print(f"PostgreSQL connection OK; pgvector {version} is enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
