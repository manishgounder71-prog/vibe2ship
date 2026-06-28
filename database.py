"""
FutureShield AI — Dual-Backend Database Interface

Supports both SQLite (development/testing) and PostgreSQL (production)
via the FUTURESHIELD_DB_URL environment variable.

- SQLite:  FUTURESHIELD_DB_URL=sqlite:///path/to/database.db  (default)
- PostgreSQL: FUTURESHIELD_DB_URL=postgresql://user:pass@host:5432/dbname

Uses a connection pool in both modes with proper context managers.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Generator

DB_URL: str = os.getenv("FUTURESHIELD_DB_URL", "")
_DB_PATH: str = os.getenv(
    "FUTURESHIELD_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db"),
)

# ─── PostgreSQL support ───────────────────────────────────────────
_use_postgres: bool = DB_URL.startswith("postgresql")
_pg_pool: Any = None  # Will hold the psycopg2 connection pool (threaded)


# ─── Connection Wrappers ──────────────────────────────────────────

class _SQLiteConnectionWrapper:
    """Wraps a sqlite3 connection so it has a consistent interface with PG."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._is_pg = False

    def cursor(self) -> sqlite3.Cursor:
        return self._conn.cursor()

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def rollback(self) -> None:
        self._conn.rollback()


class _PGConnectionWrapper:
    """Wraps a psycopg2 connection from the pool."""

    def __init__(self, pg_conn: Any) -> None:
        self._conn = pg_conn
        self._is_pg = True

    def cursor(self) -> Any:
        return self._conn.cursor()

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        global _pg_pool
        if _pg_pool is not None:
            _pg_pool.putconn(self._conn)  # type: ignore[misc]

    def rollback(self) -> None:
        self._conn.rollback()


def _init_pg_pool() -> None:
    """Initialize the PostgreSQL connection pool."""
    global _pg_pool
    if _pg_pool is not None:
        return
    try:
        import psycopg2  # type: ignore[import-untyped]
        from psycopg2 import pool as pg_pool_module  # type: ignore[import-untyped]

        _pg_pool = pg_pool_module.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DB_URL,
        )
    except ImportError:
        raise RuntimeError(
            "PostgreSQL mode requires 'psycopg2-binary'. "
            "Install it with: pip install psycopg2-binary"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to connect to PostgreSQL: {e}")


# ─── Connection management ────────────────────────────────────────

@contextmanager
def get_db_connection() -> Generator[Any, None, None]:
    """Get a database connection (SQLite or PostgreSQL).

    Yields a connection-compatible wrapper with ``cursor()``, ``commit()``,
    ``close()``, and ``rollback()`` methods plus an ``_is_pg`` attribute.
    """
    if _use_postgres:
        yield from _get_pg_connection()
    else:
        yield from _get_sqlite_connection()


def _get_sqlite_connection() -> Generator[_SQLiteConnectionWrapper, None, None]:
    """SQLite connection via context manager."""
    raw_conn = sqlite3.connect(_DB_PATH)
    raw_conn.row_factory = sqlite3.Row
    wrapper = _SQLiteConnectionWrapper(raw_conn)
    try:
        yield wrapper
    finally:
        raw_conn.close()


def _get_pg_connection() -> Generator[_PGConnectionWrapper, None, None]:
    """PostgreSQL connection from pool via context manager."""
    _init_pg_pool()
    import psycopg2  # type: ignore[import-untyped]

    raw_conn = _pg_pool.getconn()  # type: ignore[misc]
    wrapper = _PGConnectionWrapper(raw_conn)

    try:
        yield wrapper
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        try:
            _pg_pool.putconn(raw_conn)  # type: ignore[misc]
        except Exception:
            pass  # Pool might have been destroyed


# ─── Query helpers ────────────────────────────────────────────────

def _rows_to_dicts(cursor: Any, is_pg: bool = False) -> list[dict[str, Any]]:
    """Convert cursor results to list of dicts.

    Works for both sqlite3.Row and raw psycopg2 rows.
    """
    if is_pg:
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    # sqlite3 with row_factory = sqlite3.Row
    return [dict(row) for row in cursor.fetchall()]


def _translate_to_pg(sql: str) -> str:
    """Translate SQLite-flavoured SQL to PostgreSQL syntax.

    Handles: ? → %s, CURRENT_TIMESTAMP → NOW(),
    julianday → EXTRACT(EPOCH FROM ...), datetime() → INTERVAL,
    DATE() → INTERVAL.
    """
    pg = sql.replace("?", "%s")
    # DATETIME / DATE functions → PostgreSQL equivalents
    pg = pg.replace("CURRENT_TIMESTAMP", "NOW()")

    # julianday(x) → EXTRACT(EPOCH FROM x)
    # This is used in focus.py to calculate elapsed seconds.
    # IMPORTANT: julianday returns DAYS, EXTRACT(EPOCH) returns SECONDS.
    # So we must also remove any trailing * 86400 (or / 86400) that
    # converts between the two units.
    if "julianday" in pg:
        pg = pg.replace("julianday(CURRENT_TIMESTAMP)", "EXTRACT(EPOCH FROM NOW())")
        pg = pg.replace("julianday(", "EXTRACT(EPOCH FROM ")
        # Remove * 86400 (days-to-seconds for julianday), since EPOCH is already seconds
        pg = pg.replace("* 86400", "")
        pg = pg.replace("* 86400.0", "")

    # datetime('now', '-N hours') → NOW() - INTERVAL 'N hours'
    import re
    pg = re.sub(r"datetime\('now',\s*'([^']+)'\)", r"(NOW() + INTERVAL '\1')", pg)

    # DATE('now', '-N days') → CURRENT_DATE - INTERVAL 'N days'
    pg = re.sub(r"DATE\('now',\s*'([^']+)'\)", r"(CURRENT_DATE + INTERVAL '\1')", pg)

    # Remove any remaining unquoted 'now' references
    pg = pg.replace("'now'", "NOW()")

    return pg


def query_db(query: str, args: tuple[Any, ...] = (), one: bool = False) -> Any:
    """Execute a SELECT query and return results as list of dicts.

    If one=True, returns a single dict or None.
    """
    with get_db_connection() as conn:
        is_pg: bool = getattr(conn, "_is_pg", False)
        cursor = conn.cursor()
        sql = _translate_to_pg(query) if is_pg else query
        cursor.execute(sql, args)
        rv = _rows_to_dicts(cursor, is_pg)
    return (rv[0] if rv else None) if one else rv


def execute_db(query: str, args: tuple[Any, ...] = ()) -> None:
    """Execute an INSERT/UPDATE/DELETE query with commit."""
    with get_db_connection() as conn:
        is_pg: bool = getattr(conn, "_is_pg", False)
        cursor = conn.cursor()
        sql = _translate_to_pg(query) if is_pg else query
        cursor.execute(sql, args)
        conn.commit()


def insert_and_get_id(query: str, args: tuple[Any, ...] = ()) -> int:
    """Execute an INSERT and return the last inserted row ID."""
    with get_db_connection() as conn:
        is_pg: bool = getattr(conn, "_is_pg", False)
        cursor = conn.cursor()

        if is_pg:
            sql = _translate_to_pg(query)
            sql += " RETURNING id"
            cursor.execute(sql, args)
            last_id = cursor.fetchone()[0]
        else:
            cursor.execute(query, args)
            last_id = cursor.lastrowid

        conn.commit()
    return int(last_id)


# ─── Schema migration ─────────────────────────────────────────────

MIGRATIONS: list[tuple[str, str]] = [
    (
        "001_initial",
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS threats (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            urgency TEXT NOT NULL,
            probability INTEGER NOT NULL,
            success_rate TEXT NOT NULL,
            x_pos INTEGER NOT NULL,
            y_pos INTEGER NOT NULL,
            type TEXT NOT NULL,
            resolved BOOLEAN DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            progress INTEGER NOT NULL,
            deadline TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS focus_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            energy_level INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            duration_minutes INTEGER NOT NULL,
            actual_duration_seconds INTEGER DEFAULT 0,
            energy_rating INTEGER,
            session_type TEXT DEFAULT 'focus',
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS schema_version (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
]


def run_migrations() -> None:
    """Apply any pending schema migrations."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        is_pg: bool = getattr(conn, "_is_pg", False)
        sql = "CREATE TABLE IF NOT EXISTS schema_version (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        if is_pg:
            sql = sql.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TIMESTAMP DEFAULT NOW()")
        cursor.execute(sql)
        conn.commit()

    for version, raw_sql in MIGRATIONS:
        existing = query_db(
            "SELECT version FROM schema_version WHERE version = ?",
            (version,),
            one=True,
        )
        if existing:
            continue

        statements = [s.strip() for s in raw_sql.split(";") if s.strip()]
        with get_db_connection() as conn:
            is_pg: bool = getattr(conn, "_is_pg", False)
            cursor = conn.cursor()
            for stmt in statements:
                sql = _translate_to_pg(stmt) if is_pg else stmt
                sql = sql.replace("AUTOINCREMENT", "GENERATED BY DEFAULT AS IDENTITY") if is_pg else sql
                cursor.execute(sql)
            conn.commit()

        execute_db(
            "INSERT INTO schema_version (version) VALUES (?)",
            (version,),
        )


# ─── Seed data ────────────────────────────────────────────────────

def seed_default_data() -> None:
    """Insert default seed data if tables are empty."""
    threats_count = query_db("SELECT COUNT(*) as count FROM threats", one=True)
    if threats_count and threats_count["count"] == 0:
        threats_data = [
            ("XR-904", "Quantum Decoherence Gap", "HIGH", 88, "12.4%", 30, 20, "critical", 0),
            ("TR-421", "Latency Spike in Cluster 7", "MED", 42, "65.1%", 80, 60, "warning", 0),
            ("BV-112", "Unmapped Resource Call", "LOW", 12, "98.2%", 45, 45, "optimized", 0),
        ]
        for t in threats_data:
            execute_db(
                "INSERT INTO threats (id, name, urgency, probability, success_rate, x_pos, y_pos, type, resolved) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                t,
            )

    goals_count = query_db("SELECT COUNT(*) as count FROM goals", one=True)
    if goals_count and goals_count["count"] == 0:
        goals_data = [
            ("Project Phoenix Core Integration", "ACTIVE", 35, "2026-06-27"),
            ("Digital Twin Synchronization", "PENDING", 0, "2026-06-30"),
            ("FastAPI CRUD Integration", "COMPLETED", 100, "2026-06-25"),
        ]
        for title, status, progress, deadline in goals_data:
            execute_db(
                "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
                (title, status, progress, deadline),
            )

    records_count = query_db("SELECT COUNT(*) as count FROM focus_records", one=True)
    if records_count and records_count["count"] == 0:
        for level in [40, 60, 80, 95, 70, 50, 65, 85]:
            execute_db(
                "INSERT INTO focus_records (energy_level) VALUES (?)",
                (level,),
            )


def init_db() -> None:
    """Initialize the database: run migrations, then seed defaults."""
    run_migrations()
    seed_default_data()


# ─── Utility: export/import helpers ───────────────────────────────

def get_all_data() -> dict[str, Any]:
    """Export all data as a dict (for backup)."""
    return {
        "goals": query_db("SELECT * FROM goals"),
        "threats": query_db("SELECT * FROM threats"),
        "focus_records": query_db("SELECT * FROM focus_records"),
        "focus_sessions": query_db("SELECT * FROM focus_sessions"),
    }


def clear_all_data() -> None:
    """Delete all data from all tables."""
    execute_db("DELETE FROM goals")
    execute_db("DELETE FROM threats")
    execute_db("DELETE FROM focus_records")
    execute_db("DELETE FROM focus_sessions")
