"""FastAPI dependencies - error handling and shared utilities."""

from fastapi import HTTPException
from engine.db.database import get_connection


def get_db():
    """Provide a database connection."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def not_found(msg: str):
    raise HTTPException(status_code=404, detail=msg)


def bad_request(msg: str):
    raise HTTPException(status_code=400, detail=msg)
