"""Admin API Key management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from engine.db import dao_api_key
from ..auth import verify_api_key

router = APIRouter(dependencies=[], tags=["admin"])


@router.post("/keys")
def create_key(
    display_name: str = "",
    is_admin: bool = False,
    user_id: int | None = None,
    key: dict = Depends(verify_api_key),
):
    """Create a new API key. Returns the full key only once."""
    if not key.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = dao_api_key.create_key(
        display_name=display_name,
        is_admin=is_admin,
        user_id=user_id,
    )
    return {
        "key": result["key"],
        "key_prefix": result["key_prefix"],
        "id": result["id"],
        "display_name": result["display_name"],
        "is_admin": result["is_admin"],
        "warning": "Save this key — it will not be shown again",
    }


@router.get("/keys")
def list_keys(include_inactive: bool = False, key: dict = Depends(verify_api_key)):
    """List API keys (hash excluded for security)."""
    if not key.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return {"keys": dao_api_key.list_keys(include_inactive=include_inactive)}


@router.delete("/keys/{key_id}")
def revoke_key(key_id: int, key: dict = Depends(verify_api_key)):
    """Revoke an API key."""
    if not key.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    ok = dao_api_key.revoke_key(key_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found or already revoked")
    return {"revoked": True}
