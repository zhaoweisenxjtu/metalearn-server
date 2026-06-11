"""FastAPI auth dependency — API Key authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from engine.db.dao_api_key import validate_key

_bearer = HTTPBearer(auto_error=False)


def verify_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    """Verify Bearer token against stored API keys.

    Usage:
        @router.get("/protected")
        def endpoint(key: dict = Depends(verify_api_key)):
            return {"key_id": key["id"]}

    Skips auth check when auto_error=False and no credentials provided.
    Attach this as dependency to routes that require authentication.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_record = validate_key(credentials.credentials)
    if key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return dict(key_record)


# Convenience alias for routes that always require auth
require_auth = Depends(verify_api_key)
