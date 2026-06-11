"""Learning Journal API router."""

from fastapi import APIRouter
from datetime import date as date_mod
from engine.db import dao_journal
from ..schemas import JournalCreate

router = APIRouter()


@router.post("")
def create_journal(body: JournalCreate):
    return dao_journal.create_journal(
        body.user_id, body.date or date_mod.today().isoformat(),
        focus_minutes=body.focus, diffuse_minutes=body.diffuse,
        topics=body.topics, methods=body.methods,
        highlights=body.highlights, struggles=body.struggles,
        tomorrow_plan=body.tomorrow,
    )


@router.get("")
def get_journal(user_id: int, date: str):
    entry = dao_journal.get_journal_by_date(user_id, date)
    if not entry:
        return {"date": date, "user_id": user_id, "detail": "no entry"}
    return entry


@router.get("/list")
def list_journals(user_id: int, limit: int = 30):
    return dao_journal.list_journals(user_id, limit=limit)
