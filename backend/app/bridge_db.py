"""
Bridge & Highway Network Database (SQLite).
Handles: bridges, influence lines, junctions, highway graph, effect calculation cache.

MySQL compatibility: uses standard SQL types. Swap connection string for production.
"""
import json
import logging
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "cargo_bridge.db"

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    return str(DB_PATH)


def init_bridge_db():
    """Initialize bridge database from schema.sql."""
    schema_path = DATA_DIR / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    conn = sqlite3.connect(str(DB_PATH))
    try:
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
        logger.info(f"Initialized at {DB_PATH}")
    finally:
        conn.close()


@contextmanager
def get_bridge_db(readonly: bool = False):
    """Context-managed connection for bridge database."""
    conn = None
    try:
        if readonly:
            uri = f"file:{DB_PATH}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
        else:
            conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
    finally:
        if conn:
            conn.close()


def query(sql: str, params=()) -> list[dict]:
    """Execute a SELECT query and return list of dicts."""
    with get_bridge_db(readonly=True) as conn:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def query_one(sql: str, params=()) -> dict | None:
    """Execute a SELECT query and return first row or None."""
    with get_bridge_db(readonly=True) as conn:
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def execute(sql: str, params=()) -> int:
    """Execute INSERT/UPDATE/DELETE and return rowcount."""
    with get_bridge_db() as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount


def executemany(sql: str, params_list: list) -> int:
    """Execute parameterized INSERT many times."""
    with get_bridge_db() as conn:
        cursor = conn.executemany(sql, params_list)
        conn.commit()
        return cursor.rowcount
