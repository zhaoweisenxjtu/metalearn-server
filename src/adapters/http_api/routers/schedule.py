"""Schedule API router."""

from fastapi import APIRouter
from engine.scheduler.multi_track import MultiTrackScheduler

router = APIRouter()


@router.get("/today")
def schedule_today(user_id: int, minutes: int | None = None):
    return MultiTrackScheduler().get_schedule(user_id, minutes)
