"""Dashboard API router."""

from fastapi import APIRouter
from engine.core.indicators import Dashboard
from ..dependencies import not_found

router = APIRouter()


@router.get("")
def dashboard(user_id: int):
    return Dashboard().overall(user_id)


@router.get("/tracks/{track_id}")
def track_dashboard(track_id: int):
    data = Dashboard().track_summary(track_id)
    if "error" in data:
        not_found(data["error"])
    return data
