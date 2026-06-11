"""Tracks API router."""

from fastapi import APIRouter
from engine.db import dao_track
from ..dependencies import not_found

router = APIRouter()


@router.post("")
def create_track(user_id: int, name: str, type: str = "applied", priority: int = 3):
    return dao_track.create_track(user_id, name, type, priority)


@router.get("")
def list_tracks(user_id: int, status: str | None = None):
    return dao_track.list_tracks(user_id, status)


@router.get("/{track_id}")
def get_track(track_id: int):
    track = dao_track.get_track(track_id)
    if not track:
        not_found(f"Track {track_id} not found")
    return track


@router.patch("/{track_id}")
def update_track(track_id: int, name: str | None = None,
                 status: str | None = None, priority: int | None = None):
    updates = {}
    if name is not None: updates["name"] = name
    if status is not None: updates["status"] = status
    if priority is not None: updates["priority"] = priority
    track = dao_track.update_track(track_id, **updates)
    if not track:
        not_found(f"Track {track_id} not found")
    return track
