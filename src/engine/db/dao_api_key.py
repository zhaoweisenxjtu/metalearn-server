"""API Key DAO: create, validate, list, revoke."""

import hashlib
import secrets
from datetime import datetime
from .database import get_connection, row_to_dict, rows_to_dicts


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_key() -> str:
    return "ml_" + secrets.token_hex(20)


def create_key(display_name: str = "", is_admin: bool = False, user_id: int | None = None) -> dict:
    """Create a new API key. Returns the full key only at creation time."""
    raw_key = _generate_key()
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12]  # e.g. "ml_a1b2c3d4e5f6"

    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO api_keys (key_prefix, key_hash, display_name, is_admin, user_id) VALUES (?, ?, ?, ?, ?)",
            (key_prefix, key_hash, display_name, 1 if is_admin else 0, user_id),
        )
        conn.commit()
        key_id = cur.lastrowid
        return {
            "id": key_id,
            "key": raw_key,
            "key_prefix": key_prefix,
            "display_name": display_name,
            "is_admin": is_admin,
            "user_id": user_id,
        }
    finally:
        conn.close()


def validate_key(raw_key: str) -> dict | None:
    """Validate a raw key string. Returns key record if valid, None otherwise."""
    key_hash = _hash_key(raw_key)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND active = 1",
            (key_hash,),
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def list_keys(include_inactive: bool = False) -> list[dict]:
    """List all API keys (excludes hash for security)."""
    conn = get_connection()
    try:
        if include_inactive:
            rows = conn.execute(
                "SELECT id, key_prefix, display_name, is_admin, user_id, active, created_at, revoked_at "
                "FROM api_keys ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, key_prefix, display_name, is_admin, user_id, active, created_at "
                "FROM api_keys WHERE active = 1 ORDER BY created_at DESC"
            ).fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


def revoke_key(key_id: int) -> bool:
    """Revoke an API key by ID."""
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            "UPDATE api_keys SET active = 0, revoked_at = ? WHERE id = ? AND active = 1",
            (now, key_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_key_count() -> int:
    """Return number of active keys."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM api_keys WHERE active = 1").fetchone()
        return row["cnt"]
    finally:
        conn.close()
