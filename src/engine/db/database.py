"""Database connection and initialization."""

import sqlite3
import os
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _get_db_dir() -> Path:
    """Return the database directory, respecting META_LEARN_DB env var."""
    env_path = os.environ.get("META_LEARN_DB")
    if env_path:
        return Path(env_path).parent
    return Path.home() / ".meta-learning"


def _get_db_path() -> Path:
    """Return the database file path, respecting META_LEARN_DB env var."""
    env_path = os.environ.get("META_LEARN_DB")
    if env_path:
        return Path(env_path)
    return Path.home() / ".meta-learning" / "meta_learning.db"


def get_db_path() -> str:
    """Return the database file path."""
    return str(_get_db_path())


def ensure_db_dir():
    """Create the database directory if it doesn't exist."""
    _get_db_dir().mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Get a new SQLite connection with WAL mode and foreign keys."""
    ensure_db_dir()
    conn = sqlite3.connect(str(_get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(force: bool = False):
    """Initialize the database schema and run bootstrap."""
    ensure_db_dir()
    exists = _get_db_path().exists()

    if not exists or force:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        conn = get_connection()
        try:
            conn.executescript(schema)
            conn.commit()
        finally:
            conn.close()
    else:
        # Ensure api_keys table exists on existing DBs (schema addition)
        conn = get_connection()
        try:
            conn.executescript(
                "CREATE TABLE IF NOT EXISTS api_keys (\n"
                "    id            INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                "    key_prefix    TEXT    NOT NULL,\n"
                "    key_hash      TEXT    NOT NULL UNIQUE,\n"
                "    display_name  TEXT    NOT NULL DEFAULT '',\n"
                "    is_admin      INTEGER NOT NULL DEFAULT 0,\n"
                "    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,\n"
                "    active        INTEGER NOT NULL DEFAULT 1,\n"
                "    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),\n"
                "    revoked_at    TEXT\n"
                ");\n"
                "CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);\n"
            )
            conn.commit()
        finally:
            conn.close()

    # Bootstrap: create admin key from env var if no active keys exist
    bootstrap_key = os.environ.get("META_LEARN_BOOTSTRAP_KEY")
    if bootstrap_key:
        conn = get_connection()
        try:
            count = conn.execute("SELECT COUNT(*) AS cnt FROM api_keys WHERE active = 1").fetchone()["cnt"]
            if count == 0:
                from .dao_api_key import _hash_key

                key_hash = _hash_key(bootstrap_key)
                key_prefix = bootstrap_key[:12]
                conn.execute(
                    "INSERT OR IGNORE INTO api_keys (key_prefix, key_hash, display_name, is_admin) VALUES (?, ?, ?, 1)",
                    (key_prefix, key_hash, "bootstrap admin"),
                )
                conn.commit()
        finally:
            conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    """Convert a list of sqlite3.Row to a list of dicts."""
    return [dict(r) for r in rows]
